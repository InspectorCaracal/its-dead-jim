from utils.general import MergeDict

# electronics
BASE_SPEAKER = MergeDict({
	"key": "speaker",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'ElecSpeaker'}, "systems"),
		("volume",2)
	],
	"tags": [
		("speaker", "part"),
	]
})
BASE_MICROPHONE = MergeDict({
	"key": "microphone",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'ElecMicrophone'}, "systems"),
	],
	"tags": [
		("microphone", "part"),
	]
})
BASE_CPU = MergeDict({
	"key": "processing unit",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'AppDevice'}, "systems"),
	],
	"tags": [
		("cpu", "part"),
	]
})
BASE_POWER = MergeDict({
	"key": "battery",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'PowerOnOff'}, "systems"),
	],
	"tags": [
		("power_source", "part"),
	]
})
BASE_DISPLAY = MergeDict({
	"key": "display screen",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'ElecDisplay'}, "systems"),
	],
	"tags": [
		("display_screen", "part"),
	]
})
BASE_SIMCARD = MergeDict({
	"key": "simcard",
	"typeclass": "systems.electronics.things.Electronics",
	"tags": [
		("simcard", "part"),
	]
})
BASE_DATA_STORAGE = MergeDict({
	"key": "storage",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'DataReadWrite'}, "systems"),
	],
	"tags": [
		("datadrive", "part"),
	]
})
BASE_DIGICAM = MergeDict({
	"key": "camera",
	"typeclass": "systems.electronics.things.Electronics",
	"attrs": [
		("behaviors", {'CameraBehavior'}, "systems"),
	],
	"tags": [
		("camera", "part"),
	]
})

# vehicle parts