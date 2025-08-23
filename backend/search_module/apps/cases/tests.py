from django.test import TestCase
from .models import Court, Case

class CourtModelTest(TestCase):
    def test_court_creation(self):
        court = Court.objects.create(
            name="Test Court",
            code="TC"
        )
        self.assertEqual(court.name, "Test Court")
        self.assertEqual(court.code, "TC")

class CaseModelTest(TestCase):
    def test_case_creation(self):
        court = Court.objects.create(name="Test Court", code="TC")
        case = Case.objects.create(
            sr_number="TEST001",
            case_number="Test Case 1/2025",
            case_title="Test Petitioner vs Test Respondent",
            court=court
        )
        self.assertEqual(case.sr_number, "TEST001")
        self.assertEqual(case.court, court)
