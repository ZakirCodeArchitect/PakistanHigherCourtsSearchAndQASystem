"""
Optimized database saver for IHC scraper
Removed redundant fields and optimized for industry standards
"""

import os
import sys
import django
from django.db import transaction
from django.utils import timezone


# Setup Django for the scraper
def setup_django():
    """Setup Django environment for the scraper"""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    if project_root not in sys.path:
        sys.path.append(project_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


# Import models after Django setup
setup_django()
from apps.cases.models import (
    Court,
    Case,
    CaseDetail,
    JudgementData,
    OrdersData,
    CommentsData,
    CaseCmsData,
    PartiesDetailData,
    ViewLinkData,
)


class DBSaver:
    """Optimized class to save scraper data to PostgreSQL"""

    def __init__(self, court_name="Islamabad High Court", court_code="IHC"):
        self.court, _ = Court.objects.get_or_create(name=court_name, code=court_code)

    def save_case(self, case_data):
        """Save a single case to database with optimized structure"""
        try:
            with transaction.atomic():
                # Create or update main case (removed redundant fields)
                case, created = Case.objects.get_or_create(
                    sr_number=case_data.get("SR", ""),
                    case_number=case_data.get("CASE_NO", ""),
                    defaults={
                        "institution_date": case_data.get("INSTITUTION", ""),
                        "case_title": case_data.get("CASE_TITLE", ""),
                        "bench": case_data.get("BENCH", ""),
                        "hearing_date": case_data.get("HEARING_DATE", ""),
                        "status": case_data.get("STATUS", ""),
                        # REMOVED: history_options (redundant UI text)
                        # REMOVED: details (empty, redundant)
                        "court": self.court,
                    },
                )

                if not created:
                    # Only update if data has actually changed
                    data_changed = False
                    
                    # Check if any field has changed
                    if case.institution_date != case_data.get("INSTITUTION", case.institution_date):
                        case.institution_date = case_data.get("INSTITUTION", case.institution_date)
                        data_changed = True
                    if case.case_title != case_data.get("CASE_TITLE", case.case_title):
                        case.case_title = case_data.get("CASE_TITLE", case.case_title)
                        data_changed = True
                    if case.bench != case_data.get("BENCH", case.bench):
                        case.bench = case_data.get("BENCH", case.bench)
                        data_changed = True
                    if case.hearing_date != case_data.get("HEARING_DATE", case.hearing_date):
                        case.hearing_date = case_data.get("HEARING_DATE", case.hearing_date)
                        data_changed = True
                    if case.status != case_data.get("STATUS", case.status):
                        case.status = case_data.get("STATUS", case.status)
                        data_changed = True
                    
                    # Only save and update timestamp if data actually changed
                    if data_changed:
                        case.updated_at = timezone.now()
                        case.save()
                        print(f"🔄 Updated existing case {case.case_number} with new data")
                    else:
                        print(f"⏭️ Skipped existing case {case.case_number} (no changes)")
                        # Return early to avoid processing related data unnecessarily
                        return {
                            "status": "success",
                            "action": "skipped",
                            "case_number": case.case_number,
                            "message": "No changes detected"
                        }

                # Save detailed case information if available
                if case_data.get("CASE_STATUS") or case_data.get("CASE_TITLE_DETAILED"):
                    CaseDetail.objects.get_or_create(
                        case=case,
                        defaults={
                            "case_status": case_data.get("CASE_STATUS", ""),
                            "hearing_date_detailed": case_data.get(
                                "HEARING_DATE_DETAILED", ""
                            ),
                            "case_stage": case_data.get("CASE_STAGE", ""),
                            "tentative_date": case_data.get("TENTATIVE_DATE", ""),
                            "short_order": case_data.get("SHORT_ORDER", ""),
                            "before_bench": case_data.get("BEFORE_BENCH", ""),
                            "case_title_detailed": case_data.get(
                                "CASE_TITLE_DETAILED", ""
                            ),
                            "advocates_petitioner": case_data.get(
                                "ADVOCATES_PETITIONER", ""
                            ),
                            "advocates_respondent": case_data.get(
                                "ADVOCATES_RESPONDENT", ""
                            ),
                            "case_description": case_data.get("CASE_DESCRIPTION", ""),
                            "disposed_of_status": case_data.get(
                                "DISPOSED_OF_STATUS", ""
                            ),
                            "case_disposal_date": case_data.get(
                                "CASE_DISPOSAL_DATE", ""
                            ),
                            "disposal_bench": case_data.get("DISPOSAL_BENCH", ""),
                            "consigned_date": case_data.get("CONSIGNED_DATE", ""),
                            "fir_number": case_data.get("FIR_NUMBER", ""),
                            "fir_date": case_data.get("FIR_DATE", ""),
                            "police_station": case_data.get("POLICE_STATION", ""),
                            "under_section": case_data.get("UNDER_SECTION", ""),
                            "incident": case_data.get("INCIDENT", ""),
                            "name_of_accused": case_data.get("NAME_OF_ACCUSED", ""),
                        },
                    )

                # Save normalized history data (removed redundant JSON storage)
                self._save_orders_data(case, case_data, source_type='main')
                self._save_comments_data(case, case_data, source_type='main')
                self._save_case_cms_data(case, case_data, source_type='main')
                self._save_judgement_data(case, case_data)

                # Save detail options data (detail page data)
                self._save_parties_detail_data(case, case_data)
                # Save detail page data with appropriate source types
                if case_data.get("COMMENTS_DETAIL_DATA"):
                    self._save_comments_data(case, case_data, source_type='detail')
                if case_data.get("CASE_CMS_DETAIL_DATA"):
                    self._save_case_cms_data(case, case_data, source_type='detail')
                if case_data.get("HEARING_DETAILS_DETAIL_DATA"):
                    self._save_orders_data(case, case_data, source_type='hearing')

                # REMOVED: CaseHistoryData and CaseDetailOptionsData - redundant JSON storage
                # The data is already stored in normalized tables above

                return {
                    "status": "success",
                    "case_id": case.id,
                    "case_number": case.case_number,
                    "message": f"✅ Case {case.case_number} saved to database",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "case_number": case_data.get("CASE_NO", "Unknown"),
            }

    def _save_orders_data(self, case, case_data, source_type='main'):
        """Save orders data"""
        orders_data = case_data.get("ORDERS_DATA", {})
        if orders_data and orders_data.get("rows"):
            for row in orders_data["rows"]:
                if len(row) >= 8:
                    OrdersData.objects.get_or_create(
                        case=case,
                        sr_number=row[0] if len(row) > 0 else "",
                        source_type=source_type,
                        defaults={
                            "hearing_date": row[1] if len(row) > 1 else "",
                            "bench": row[2] if len(row) > 2 else "",
                            "list_type": row[3] if len(row) > 3 else "",
                            "case_stage": row[4] if len(row) > 4 else "",
                            "short_order": row[5] if len(row) > 5 else "",
                            "disposal_date": row[6] if len(row) > 6 else "",
                            "view_link": row[7] if len(row) > 7 else [],
                        },
                    )

    def _save_comments_data(self, case, case_data, source_type='main'):
        """Save comments data"""
        comments_data = case_data.get("COMMENTS_DATA", {})
        if comments_data and comments_data.get("rows"):
            for row in comments_data["rows"]:
                if len(row) >= 8:
                    CommentsData.objects.get_or_create(
                        case=case,
                        compliance_date=row[1] if len(row) > 1 else "",
                        case_no=row[2] if len(row) > 2 else "",
                        source_type=source_type,
                        defaults={
                            "case_title": row[3] if len(row) > 3 else "",
                            "doc_type": row[4] if len(row) > 4 else "",
                            "parties": row[5] if len(row) > 5 else "",
                            "description": row[6] if len(row) > 6 else "",
                            "view_link": row[7] if len(row) > 7 else [],
                        },
                    )

    def _save_case_cms_data(self, case, case_data, source_type='main'):
        """Save case CMs data"""
        case_cms_data = case_data.get("CASE_CMS_DATA", {})
        if case_cms_data and case_cms_data.get("rows"):
            for row in case_cms_data["rows"]:
                if len(row) >= 7:
                    CaseCmsData.objects.get_or_create(
                        case=case,
                        sr_number=row[0] if len(row) > 0 else "",
                        source_type=source_type,
                        defaults={
                            "cm": row[1] if len(row) > 1 else "",
                            "institution": row[2] if len(row) > 2 else "",
                            "disposal_date": row[3] if len(row) > 3 else "",
                            "order_passed": row[4] if len(row) > 4 else "",
                            "description": row[5] if len(row) > 5 else "",
                            "status": row[6] if len(row) > 6 else "",
                        },
                    )

    def _save_judgement_data(self, case, case_data):
        """Save judgement data (removed redundant page_title)"""
        judgement_data = case_data.get("JUDGEMENT_DATA", {})
        if judgement_data:
            JudgementData.objects.get_or_create(
                case=case,
                defaults={
                    "pdf_url": judgement_data.get("pdf_url", ""),
                    "pdf_filename": judgement_data.get("pdf_filename", ""),
                    # REMOVED: page_title (empty, redundant)
                },
            )

    def _save_parties_detail_data(self, case, case_data):
        """Save parties detail data"""
        parties_data = case_data.get("PARTIES_DETAIL_DATA", {})
        if parties_data and parties_data.get("rows"):
            for row in parties_data["rows"]:
                if len(row) >= 3:
                    PartiesDetailData.objects.get_or_create(
                        case=case,
                        party_number=row[0] if len(row) > 0 else "",
                        defaults={
                            "party_name": row[1] if len(row) > 1 else "",
                            "party_side": row[2] if len(row) > 2 else "",
                        },
                    )


