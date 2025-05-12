from rest_framework import permissions

class CanAssignPermissionsAssignedUser(permissions.BasePermission):
    def has_permission(self, request, view):
         return request.user.has_perm('AquaSmart.asignar_permisos') 
class CanViewPermissionsAssignedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('AquaSmart.ver_permisos_asignados')
class CanRemovePermissionsAssigneduser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('AquaSmart.quitar_permisos_asignados')
class CanViewGroupsAssignedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('AquaSmart.ver_roles_asignados')
class CanAssignGroupsAssignedUser(permissions.BasePermission):
    def has_permission(self, request, view):
         return request.user.has_perm('AquaSmart.asignar_roles_asignados')    
class CanRemoveGroupsAssignedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('AquaSmart.quitar_roles_asignados')        
     
