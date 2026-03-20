class EmpresaRouter:
    """
    Um roteador para controlar todas as operações de banco de dados
    do app 'orders' para o banco 'empresa'.
    """
    
    route_app_labels = {'orders'}

    def db_for_read(self, model, **hints):
        """Aponta leituras do app orders para o MySQL."""
        if model._meta.app_label in self.route_app_labels:
            return 'empresa'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Bloqueia escritas no banco da empresa se o usuário não tiver permissão.
        Se você tiver permissão de UPDATE (mas não ALTER), pode retornar 'empresa'.
        Por segurança, vamos manter 'empresa' e o banco rejeita se não der.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'empresa'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relações se ambos estiverem no mesmo banco."""
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        NUNCA tenta rodar migrate (criar tabelas) no banco da empresa.
        """
        if app_label in self.route_app_labels:
            return False
        return True