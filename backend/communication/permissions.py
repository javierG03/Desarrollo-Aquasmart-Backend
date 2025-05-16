from rest_framework import permissions


class CanAssignUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('communication.can_be_assigned')        
     