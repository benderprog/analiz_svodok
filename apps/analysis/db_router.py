class PortalRouter:
    portal_app_labels = {"analysis"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "analysis" and model._meta.managed is False:
            return "portal"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "analysis" and model._meta.managed is False:
            return "portal"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "analysis":
            return db == "default"
        return None
