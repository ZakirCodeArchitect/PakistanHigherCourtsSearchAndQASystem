"""
Database router for law_information app
Routes law_information models to the law_information database
"""

class LawInformationRouter:
    """
    A router to control all database operations on models in the
    law_information application.
    """
    
    def db_for_read(self, model, **hints):
        """Point all read operations on law_information models to law_information database."""
        if model._meta.app_label == 'law_information':
            return 'law_information'
        return None

    def db_for_write(self, model, **hints):
        """Point all write operations on law_information models to law_information database."""
        if model._meta.app_label == 'law_information':
            return 'law_information'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if a model in the law_information app is involved."""
        db_set = {'law_information', 'default'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that the law_information app's models get created on the right database."""
        if app_label == 'law_information':
            return db == 'law_information'
        elif db == 'law_information':
            return False
        return None
