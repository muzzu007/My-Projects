class_name Enemy
extends Area2D
var speed:int = 80

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	randomize()
	position=Vector2(randi_range(0,400),0)


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	position.y+=speed*delta


func _on_area_entered(area: Area2D) -> void:
	if area.name=="bulletArea":
		area.get_parent().queue_free()
		queue_free() # Replace with function body.
