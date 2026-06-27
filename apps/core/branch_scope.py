"""تصفية البيانات حسب فرع المستخدم."""


def user_branch_id(user):
    if user and getattr(user, 'branch_id', None):
        return user.branch_id
    return None


def filter_by_branch(qs, user, field='branch_id'):
    branch_id = user_branch_id(user)
    if branch_id:
        return qs.filter(**{field: branch_id})
    return qs
