bl_info = {
    "name": "ShapeKey Helpers",
    "author": "Ott, Jan",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "description": "Adds three operators: 'Split Shapekeys', 'Apply Modifiers and Keep Shapekeys' and 'Apply Selected Shapekey as Basis'",
    "warning": "",
    "wiki_url": "https://blenderartists.org/t/addon-shapekey-helpers/1131849",
    "category": "'Mesh",
}

import bpy
from inspect import currentframe, getframeinfo


#__________________________________________________________________________
#__________________________________________________________________________


def SetActiveShapeKey (name):
    bpy.context.object.active_shape_key_index = bpy.context.object.data.shape_keys.key_blocks.keys().index(name)
    
#__________________________________________________________________________
#__________________________________________________________________________

O = bpy.ops

class ShapeKeySplitter(bpy.types.Operator):
    """Creates a new object with the shapekeys split based on two vertex groups, named 'left' and 'right', that you must create manually"""
    bl_idname = "object.shape_key_splitter"
    bl_label = "Split Shapekeys"

    def execute(self, context):
        
        O.object.select_all(action='DESELECT')
        bpy.context.active_object.select_set(True)
        #____________________________
        #Generate copy of object
        #____________________________
        originalName = bpy.context.object.name
        O.object.duplicate_move()
        bpy.context.object.name = originalName + "_SplitShapeKeys"


        listOfKeys = []

        index = 0

        #__________________________________________________

        for s_key in bpy.context.object.data.shape_keys.key_blocks:
            
            if(index == 0):
                index = index + 1
                continue 
            
            if s_key.name.endswith('.L') or s_key.name.endswith('.R') or s_key.name.endswith('.B'):
                continue
            
            
            listOfKeys.append(s_key.name)

        #__________________________________________________

        for name in listOfKeys:
            
            SetActiveShapeKey(name)
            
            savedName = name
            savedShapeKey = bpy.context.object.active_shape_key
            
            
            #Create left version
            
            O.object.shape_key_clear()
            
            SetActiveShapeKey(savedName)
            savedShapeKey.vertex_group = 'left'
            savedShapeKey.value = 1.0
            
            O.object.shape_key_add(from_mix=True)
            bpy.context.object.active_shape_key.name = savedName + ".L"

            
            #Create right version
            
            O.object.shape_key_clear()
            
            SetActiveShapeKey(savedName)
            savedShapeKey.vertex_group = 'right'
            savedShapeKey.value = 1.0
            
            O.object.shape_key_add(from_mix=True)
            bpy.context.object.active_shape_key.name = savedName + ".R"
            
            
        for name in listOfKeys:
            
            #Set index to target shapekey
            SetActiveShapeKey(name)
            #Remove
            O.object.shape_key_remove(all=False)
                
                
        return {'FINISHED'}
    

class ShapeKeyPreserver(bpy.types.Operator):
    """Creates a new object with all modifiers applied and all shape keys preserved"""
    """NOTE: Blender can only combine objects with a matching number of vertices. """ 
    """As a result, you need to make sure that your shape keys don't change the number of vertices of the mesh. """
    """Modifiers like 'Subdivision Surface' can always be applied without any problems, other modifiers like 'Bevel' or 'Edgesplit' may not."""

    bl_idname = "object.shape_key_preserver"
    bl_label = "Apply Modifiers and Keep Shapekeys"
    
    def execute(self, context):
    
        oldName = bpy.context.active_object.name
        
        #Change context to 'VIEW_3D' and store old context
        oldContext = bpy.context.area.type
        bpy.context.area.type = 'VIEW_3D'

        #selection setup
        originalObject = bpy.context.active_object

        originalObject.select_set(True)

        listOfShapeInstances = []
        listOfShapeKeyValues = []

        #_______________________________________________________________

        #Deactivate any armature modifiers
        for mod in originalObject.modifiers:
            if mod.type == 'ARMATURE':
                originalObject.modifiers[mod.name].show_viewport = False

        index = 0
        for shapekey in originalObject.data.shape_keys.key_blocks:
            if(index == 0):
                index = index + 1
                continue
            listOfShapeKeyValues.append(shapekey.value)

        index = 0
        for shapekey in originalObject.data.shape_keys.key_blocks:
            
            if(index == 0):
                index = index + 1
                continue
            
            bpy.ops.object.select_all(action='DESELECT')
            originalObject.select_set(True)

            bpy.context.view_layer.objects.active = originalObject
            
            bpy.ops.object.shape_key_clear()
            
            shapekey.value = 1.0
            
            #save name
            #____________________________
            shapekeyname = shapekey.name
            
            #create new object from shapekey and add it to list
            #____________________________
            bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
            bpy.ops.object.convert(target='MESH')
            listOfShapeInstances.append(bpy.context.active_object)
            
            #rename new object
            #____________________________
            bpy.context.object.name = shapekeyname
            
            bpy.ops.object.select_all(action='DESELECT')
            originalObject.select_set(True)

            bpy.context.view_layer.objects.active = originalObject

        #_____________________________________________________________
        #Prepare final empty container model for all those shape keys:
        #_____________________________________________________________
        
        bpy.context.view_layer.objects.active = originalObject
        bpy.ops.object.shape_key_clear()

        bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
        newObject = bpy.context.active_object

        bpy.ops.object.shape_key_clear()
        bpy.ops.object.shape_key_remove(all=True)

        newObject.name = oldName + "_Applied"

        for mod in newObject.modifiers:
            # Not actually sure why this is necessary, but blender crashes without it. :| - Stel
            bpy.ops.object.mode_set(mode = 'EDIT')            
            bpy.ops.object.mode_set(mode = 'OBJECT')            
            if mod.type != 'ARMATURE':
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)

        errorDuringShapeJoining = False
            
        for object in listOfShapeInstances:
            
            bpy.ops.object.select_all(action='DESELECT')
            newObject.select_set(True)
            object.select_set(True)

            bpy.context.view_layer.objects.active = newObject
      
            
            print("Trying to join shapes.")
            
            result = bpy.ops.object.join_shapes()
            
            if(result != {'FINISHED'}):
                print ("Could not add " + object.name + " as shape key.")
                errorDuringShapeJoining = True

        if(errorDuringShapeJoining == False):
            print("Success!")
                
        if(errorDuringShapeJoining == False):
            #Reset old shape key values on new object
            index = 0
            for shapekey in newObject.data.shape_keys.key_blocks:
                if(index == 0):
                    index = index + 1
                    continue
                shapekey.value = listOfShapeKeyValues[index-1]
                index = index + 1

        #Reset old shape key values on original object
        index = 0
        for shapekey in originalObject.data.shape_keys.key_blocks:
            if(index == 0):
                index = index + 1
                continue
            shapekey.value = listOfShapeKeyValues[index-1]
            index = index + 1
            
            
        #Select and delete all temporal shapekey objects       
        bpy.ops.object.select_all(action='DESELECT')

        for object in listOfShapeInstances:
            object.select_set(True)
            
        bpy.ops.object.delete(use_global=False)
        
        
        #Reactivate armature modifiers on old and new object
    
        for mod in originalObject.modifiers:
            if mod.type == 'ARMATURE':
                originalObject.modifiers[mod.name].show_viewport = True

        for mod in newObject.modifiers:
            if mod.type == 'ARMATURE':
                newObject.modifiers[mod.name].show_viewport = True
                
        bpy.context.area.type = oldContext
        
        return {'FINISHED'}
    
    
    
class ShapeKeyApplier(bpy.types.Operator):
    """Replace the 'Basis' shape key with the currently selected shape key"""
    bl_idname = "object.shape_key_applier"
    bl_label = "Apply Selected Shapekey as Basis"
    
    def execute(self, context):
        
        O.object.select_all(action='DESELECT')
        bpy.context.object.select_set(True)

        #____________________________
        #Generate copy of object
        #____________________________
        originalName = bpy.context.object.name
        O.object.duplicate_move()
        bpy.context.object.name = originalName + "_Applied_Shape_Key"

        shapeKeyToBeApplied_name = bpy.context.object.active_shape_key.name

        listOfKeys = []

        #__________________________________________________
        #Store all shape keys in a list 
        #__________________________________________________

        for s_key in bpy.context.object.data.shape_keys.key_blocks:
            
            if s_key.name == shapeKeyToBeApplied_name:
                continue
            
            listOfKeys.append(s_key.name)

        #__________________________________________________

        for name in listOfKeys:
            
            SetActiveShapeKey(name)
            currentShapeKey = bpy.context.object.active_shape_key
            
            SetActiveShapeKey(shapeKeyToBeApplied_name)
            applyShapeKey = bpy.context.object.active_shape_key
            
            #Add new shapekey from mix
            O.object.shape_key_clear()
            
            currentShapeKey.value = 1.0
            applyShapeKey.value = 1.0
            
            O.object.shape_key_add(from_mix=True)
            bpy.context.object.active_shape_key.name = currentShapeKey.name + "_"
            
            
        for name in listOfKeys:
            
            #Set index to target shapekey
            SetActiveShapeKey(name)
            #Remove
            O.object.shape_key_remove(all=False)
            
            
        SetActiveShapeKey(shapeKeyToBeApplied_name)
        O.object.shape_key_remove(all=False)

        #Remove the "_" at the end of each shapeKey
        for s_key in bpy.context.object.data.shape_keys.key_blocks:
            
            s_key.name = s_key.name[:-1]
            
            
        return {'FINISHED'}




# I'm honestly not sure how to add this to an existing menu in 2.8, so rather than go
# down a rabbit-hole of research, I'm just adding a panel, because it works and is
# quick to do. Someone should probably look at this and do better than I have.
class PT_shapeKeyHelpers(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Shapekey tools"
    bl_idname = "SHAPEHELPER_PT_uipanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"


    
    @classmethod
    def poll(cls, context):
        return bpy.context.active_object.type == 'MESH'

    
    def draw(self, context):
        self.layout.separator()
        self.layout.operator(ShapeKeySplitter.bl_idname, text="Split Shapekeys", icon="FULLSCREEN_ENTER")
        self.layout.operator(ShapeKeyPreserver.bl_idname, text="Apply Modifiers and Keep Shapekeys", icon="MODIFIER")
        self.layout.operator(ShapeKeyApplier.bl_idname, text="Apply Selected Shapekey as Basis", icon="KEY_HLT")


classes = (
    ShapeKeySplitter,
    ShapeKeyPreserver,
    ShapeKeyApplier,
    PT_shapeKeyHelpers

)
    

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)



if __name__ == "__main__":
    register()
    
   
