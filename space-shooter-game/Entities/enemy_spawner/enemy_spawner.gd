extends Node
var enemy_scene=preload("res://Entities/Enemy/enemy.tscn")

# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	get_parent().get_node("boundary").connect("area_entered",self._the_end)
	var timer=Timer.new()
	add_child(timer)
	timer.wait_time=2.0
	timer.connect("timeout",self._createEnemy)
	timer.start()
	# Replace with function body.
func _the_end(area:Node):
	if area is Enemy:
		get_tree().set_pause(true)
		
	

# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	pass
func _createEnemy():
	var enemy=enemy_scene.instantiate()
	get_parent().get_node("enemies").add_child(enemy)
	
