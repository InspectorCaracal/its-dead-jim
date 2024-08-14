from utils.menus import MenuTree

class DemoMenu(MenuTree):
  _header = "Header"
  _footer = "Footer"

  @property
  def _suffix_options(self):
    return [{"desc": "Get me out of here!", "goto": "menunode_end"}] 

  def menunode_start(self, caller, *args, **kwargs):
    text = "Welcome to the test of the Menu Class system. Please keep your hands and feet inside the ride at all times."
    options = {"desc": "Wheeeee", "goto": "menunode_ride"}

    return text, options
  
  def menunode_ride(self, caller, *args, **kwargs):
    text = "(( WHHHOOOOOOOOOSHHHHHH ))"
    options = {"desc": "Wheeeee", "goto": "menunode_ride"}

    return text, options

  def menunode_end(self, caller, *args, **kwargs):
    return "Thank you for participating in this test.", {}