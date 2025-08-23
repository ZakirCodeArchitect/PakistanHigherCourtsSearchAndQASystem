from django.shortcuts import render
from django.http import JsonResponse
from .models import Case, Court

def case_list(request):
    """Simple view to list cases"""
    cases = Case.objects.all()[:10]  # Get first 10 cases
    return JsonResponse({
        'total_cases': Case.objects.count(),
        'cases': list(cases.values('sr_number', 'case_number', 'case_title', 'status'))
    })

def court_list(request):
    """Simple view to list courts"""
    courts = Court.objects.all()
    return JsonResponse({
        'courts': list(courts.values('name', 'code'))
    })
