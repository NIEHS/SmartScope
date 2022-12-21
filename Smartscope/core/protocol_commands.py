from Smartscope.lib.transformations import add_IS_offset
from math import cos, radians


def setAtlasOptics(scope,params,instance) -> None:
    scope.set_atlas_optics()

def atlas(scope,params,instance) -> None:
    scope.atlas(size=[params.atlas_x,params.atlas_y],file=instance.raw)

def realignToSquare(scope,params,instance):
    from Smartscope.core.db_manipulations import set_or_update_refined_finder
    stageX, stageY, stageZ = scope.realign_to_square()
    set_or_update_refined_finder(instance.square_id, stageX, stageY, stageZ)
    scope.moveStage(stageX,stageY,stageZ)   

def square(scope,params,instance) -> None:
    scope.square(file=instance.raw)

def moveStage(scope,params,instance) -> None:
    finder = instance.finders.first()
    stage_x, stage_y, stage_z = finder.stage_x, finder.stage_y, finder.stage_z
    scope.moveStage(stage_x,stage_y,stage_z)

def eucentricSearch(scope,params,instance):
    scope.eucentricHeight()

def eucentricMediumMag(scope,params,instance):
    scope.eucentricity()

def mediumMagHole(scope,params,instance):
    scope.medium_mag_hole(params.tilt_angle,file=instance.raw)

def alignToHoleRef(scope,params,instance):
    scope.align_to_hole_ref()

def highMag(scope, params,instance):
    finder = instance.finders.first()
    stage_x, stage_y, _ = scope.report_stage()
    grid = instance.grid_id
    grid_type = grid.holeType
    grid_mesh = grid.meshMaterial
    offset = 0
    if params.offset_targeting and (grid.collection_mode == 'screening' or params.offset_distance != -1) and grid_type.hole_size is not None:
        offset = add_IS_offset(grid_type.hole_size, grid_mesh.name, offset_in_um=params.offset_distance)
    isX, isY = stage_x - finder.stage_x + offset, (stage_y - finder.stage_y) * cos(radians(round(params.tilt_angle, 1)))
    scope.image_shift_by_microns(isX,isY,params.tilt_angle)
    frames = scope.highmag(isX, isY, round(params.tilt_angle, 1), file=instance.raw,
                            frames=params.save_frames, earlyReturn=any([params.force_process_from_average, params.save_frames is False]))
    instance.is_x=isX
    instance.is_y=isY
    instance.offset=offset
    instance.frames=frames
    return instance    


protocolCommandsFactory = dict(
    setAtlasOptics=setAtlasOptics,
    atlas=atlas,
    realignToSquare=realignToSquare,
    square=square,
    moveStage=moveStage,
    eucentricSearch=eucentricSearch,
    eucentricMediumMag=eucentricMediumMag,
    mediumMagHole=mediumMagHole,
    alignToHoleRef=alignToHoleRef,
    highMag=highMag,
)