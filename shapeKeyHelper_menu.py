bl_info = {
    "name": "ShapeKey Helpers",
    "author": "Ott, Jan, Tyler Walker (BeyondDev)",
    "version": (1, 2, 0),
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


# Beyond Dev
def driver_settings_copy(copy_drv, tar_drv):
    scn_prop = bpy.context.scene.skmp_props

    tar_drv.driver.type = copy_drv.driver.type
    tar_drv.driver.use_self = copy_drv.driver.use_self

    for var in copy_drv.driver.variables:
        new_var = tar_drv.driver.variables.new()
        new_var.name = var.name
        new_var.type = var.type

        count = 0
        for tar in var.targets:
            new_var.targets[count].bone_target = tar.bone_target
            new_var.targets[count].data_path = tar.data_path

            if scn_prop.rename_driver_bones:
                new_var.targets[count].bone_target = tar.bone_target.replace(
                    scn_prop.text_filter, scn_prop.text_rename)
                new_var.targets[count].data_path = tar.data_path.replace(
                    scn_prop.text_filter, scn_prop.text_rename)

            new_var.targets[count].id = tar.id
            new_var.targets[count].transform_space = tar.transform_space
            new_var.targets[count].transform_type = tar.transform_type

            count += 1

    tar_drv.driver.expression = copy_drv.driver.expression
    print('copied driver settings...!')
    return

# Beyond Dev
def copy_drivers(copy_ob, tar_ob, copy_key, tar_key):
    copy_sk = copy_ob.data.shape_keys
    copy_drivers = copy_sk.animation_data.drivers

    if tar_ob.data.animation_data == None:
        tar_ob.data.animation_data_create()
    tar_sk = tar_ob.data.shape_keys

    for drv in copy_drivers:
        drv_name = drv.data_path.replace('key_blocks["', '')
        drv_name = drv_name.replace('"].value', '')

        if copy_key.name == drv_name:
            # new_driver = tar_sk.key_blocks[len(
            #     tar_sk.key_blocks)-1].driver_add('value', -1)
            new_driver = tar_sk.key_blocks[tar_key.name].driver_add('value', -1)
            print('executing copy...')
            driver_settings_copy(drv, new_driver)


class ShapeKeyPreserver(bpy.types.Operator):
    """Creates a new object with all modifiers applied and all shape keys + DRIVERS preserved"""
    """NOTE: Blender can only combine objects with a matching number of vertices. """ 
    """As a result, you need to make sure that your shape keys don't change the number of vertices of the mesh. """
    """Modifiers like 'Subdivision Surface' can always be applied without any problems, other modifiers like 'Bevel' or 'Edgesplit' may not."""

    bl_idname = "object.shape_key_preserver"
    bl_label = "Apply Modifiers and Keep Shapekeys+Drivers"
    
    @classmethod 
    def poll(cls, context):
        global updatedObject
        updatedObject = bpy.context.active_object
        return updatedObject and updatedObject.type == 'MESH'
    
    def execute(self, context):
        global updatedObject
    
        oldName = bpy.context.active_object.name
        
        #Change context to 'VIEW_3D' and store old context
        oldContext = bpy.context.area.type
        bpy.context.area.type = 'VIEW_3D'

        #selection setup, preserve drivers on this object
        driverObject = bpy.context.active_object

        #copy of driverObject to transfer everything from
        bpy.ops.object.duplicate(
            {"object" : driverObject,
            "selected_objects" : [driverObject]},
            linked = False
        )
        #store reference to copy of driver object
        originalObject = bpy.context.active_object

        #delete all drivers on this new object to allow proper shapekey transfer. Shapekeys cannot be modified while drivers exist on them.
        for shapekey in originalObject.data.shape_keys.key_blocks:
            # for driver in shapekey.id_data.animation_data.drivers:
            #     shapekey.driver_remove(driver.data_path)

            try:
                shapekey_name = shapekey.name
                shapekeys = originalObject.data.shape_keys
                drivers = shapekeys.animation_data.drivers
                dr = drivers.find(f'key_blocks["{shapekey_name}"].value')
                if dr is not None:
                    drivers.remove(dr)
            except:
                pass

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

        for mod in newObject.modifiers:
            # Not actually sure why this is necessary, but blender crashes without it. :| - Stel
            bpy.ops.object.mode_set(mode = 'EDIT')            
            bpy.ops.object.mode_set(mode = 'OBJECT')            
            if mod.type != 'ARMATURE':
                if (2, 90, 0) > bpy.app.version:
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)
                else:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
        
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

            driverObject.select_set(True)
            newObject.select_set(True)
            bpy.context.view_layer.objects.active = newObject

            index = 0
            for shapekey, driverShapekey in zip(newObject.data.shape_keys.key_blocks, driverObject.data.shape_keys.key_blocks):                
                if(index == 0):
                    index = index + 1
                    continue
                shapekey.value = listOfShapeKeyValues[index-1]
                index = index + 1
                #BEYOND DEV: Copy Drivers from old object to new object
                if driverShapekey.has_driver():
                    copy_drivers(driverObject, newObject, driverShapekey, shapekey)

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

        #delete all drivers on new object that did not exist on original object
        for shapekey in newObject.data.shape_keys.key_blocks:
            # if shapekey name doesn't exist in original object, delete it
            if shapekey.name not in newObject.data.shape_keys.key_blocks:
                newObject.shape_key_remove(shapekey.name)

        
        #Reactivate armature modifiers on old and new object
    
        for mod in originalObject.modifiers:
            if mod.type == 'ARMATURE':
                originalObject.modifiers[mod.name].show_viewport = True

        for mod in newObject.modifiers:
            if mod.type == 'ARMATURE':
                newObject.modifiers[mod.name].show_viewport = True

        
        # Delete the copy object
        bpy.data.objects.remove(originalObject)

        # Hide driver backup object
        driverObject.hide = True

        newObject.name = oldName + "_Applied"

                
        bpy.context.area.type = oldContext

        #Beyond Dev - For other scripts to check identify the new object
        self.updatedObject = newObject
        
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



# Ott / Jan :
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
        self.layout.operator(ShapeKeyPreserver.bl_idname, text="Apply Modifiers and Keep Shapekeys", icon="MODIFIER") # TODO: Use this to Apply Rig Modifier to Avatar
        self.layout.operator(ShapeKeyApplier.bl_idname, text="Apply Selected Shapekey as Basis", icon="KEY_HLT") # TODO: Can use this for Applying Body Type in Avatar Generator


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
    
   
