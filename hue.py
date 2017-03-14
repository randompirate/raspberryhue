#!/usr/bin/python3
import phue
import json
import random as rng
import time, datetime
from Repeater import repeater, time_delta # Timed effects
import argparse #Accept cli arguments
import sys #Accept cli arguments
from copy import deepcopy # Copy dicts

BRIDGES = {
  'Tom'  : {'ip': '192.168.1.64', 'uname': 'Bn9mIZRqKwNlxrZMQXziPcmDeCipnDuYrbokMOfS'},
  'Chris': {'ip': '192.168.1.51', 'uname': 'lQtxve5Dd6fkurmkpDmlpTNfuT8zqbN0-LNYuFfI'},
  }

HUE_RANGE = [0, 65535]


#Available command line commands
COMMANDS = {
  # 'default'   : 'default',
  'off'         : 'off',
  'on'          : 'on',
  'random_col'  : 'random_col',
  # 'run_effect'  : 'run_effect',
  'register'    : 'register',
  'blink_alert' : 'blink_alert',
  'state'       : 'state',
  'breathe'     : 'breathe',
  'dim'         : 'dim',
  'slide'       : 'slide',
}

# Commands that accept a duration
COMMANDS_DURATION = [
  COMMANDS['breathe'],
]

COMMANDS_JSON = [
  COMMANDS['breathe'],
  COMMANDS['dim'],
  COMMANDS['random_col']
]


def do_connect(bridge):
  """Connect to the bridge, create a username (BRIDGE_UNAME)
  Requires hitting the button on the brdige
  """
  bridge.connect()
  return bridge.ip, bridge.username


####################
# Controller class #
####################

class Light_controller():
  """Light controller keeps an internal overview of the light states on which to operate. This state is pushed to the lights."""
  def __init__(self):
    self.bridge = None # No bridge set yet
    self.state = {}
    self.lights = []

  def set_bridge(self, bridge_ip, bridge_uname):
    """Add bridge to this controller object"""
    self.bridge = phue.Bridge(bridge_ip, bridge_uname)
    # Pull initial state
    self.pull_light_names()
    self.pull_state()

  def pull_light_names(self):
    """Return a list of light names attached to the caurrent bridge (strings)"""
    self.lights = [name for name in self.bridge.get_light_objects('name')]
    return self.lights

  def pull_state(self):
    """Update the internal state of the lights."""
    self.state = {}
    for k, i in controller.bridge.get_api()['lights'].items():
      light_name = i['name']
      self.state[light_name] = {key : item for key, item in i['state'].items() if key in ['on', 'sat', 'bri', 'hue']}
      self.state[light_name]['transition_seconds'] = 0
      self.state[light_name]['changed'] = False
    return self.state

  def alter_lights_state(self, light_names, new_state):
    """Alter the internal state of a list of lights. Used before pushin the state to the bridge"""
    for light_name in light_names:
      for key, item in new_state.items():
        if key in ['on', 'sat', 'bri', 'hue', 'transition_seconds'] and self.state[light_name][key] != item:  #Check if truly an update
          self.state[light_name]['changed'] = 'True'
          self.state[light_name][key] = item

  def push_state(self):
    """Push the internal light state to the bridge"""
    for light, light_state in self.state.items():
      if light_state['changed']: #Only push if this light's state has been changed internally
        command = {key:item for key, item in light_state.items() if key in ['on', 'sat', 'bri', 'hue']}
        command['transitiontime'] = int(light_state['transition_seconds']*10) #Multiply and floor transition time
        if not command['on']:
          del(command['transitiontime'])    # Don't send transition time if turning off.
        self.bridge.set_light(light, command)
        light_state['changed'] = False

  def print_state(self):
    """Print light states to console in a grid"""
    ret = ''
    ret = '{:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}\n'.format('Light', 'On', 'Hue', 'Sat', 'Bright', 'Transit', 'Changed')
    for light, light_state in sorted(self.state.items()):
      ret = ret + '{:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}\n'.format(
                light,
                ('x' if light_state['on'] else ''),
                light_state['hue'],
                light_state['sat'],
                light_state['bri'],
                light_state['transition_seconds'],
                ('x' if light_state['changed'] else '')
          )
    ret = ret + '\n'
    return ret


########################## #
# Light effect functions   #
# to be used with Repeater #
############################


def effect_breathe(controller, lights, transition_seconds, brightness_range = [180, 255]):
  """Implement a breathing effect on bri"""
  low, high = brightness_range
  mid = (low + high) / 2

  # Change light state in controller
  for light in lights:
    old_brightness = controller.state[light]['bri']
    new_state = {'bri' : low if old_brightness > mid else high, 'transition_seconds' : transition_seconds }
    controller.alter_lights_state([light], new_state)

  # Make the controller push the state to the light
  controller.push_state()

def effect_hue_slide(controller, lights, transition_seconds, speed = 1000):

  for light in lights:
    new_hue = (controller.state[light]['hue'] + speed)%HUE_RANGE[1]
    # Change light state in controller
    new_state = {'hue' : new_hue, 'transition_seconds' : transition_seconds}
    controller.alter_lights_state([light], new_state)

  # Make the controller push the state to the light
  controller.push_state()

def effect_random_hue(controller, light, transition_seconds, hue_range = HUE_RANGE):
  """Implement a breathing effect on bri"""
  new_hue = rng.randint(*hue_range)
  # Change light state in controller
  new_state = {'hue' : new_hue, 'transition_seconds' : transition_seconds}
  controller.alter_lights_state([light], new_state)

  # Make the controller push the dee to the light
  controller.push_state()

def effect_swap(controller, two_lights, transition_seconds):
  light1, light2 = two_lights

  light1_state = deepcopy(controller.state[light1])
  light2_state = deepcopy(controller.state[light2])
  new_state1 = dict([[key, item] for [key, item] in light2_state.items() if key in ['on', 'hue', 'bri', 'sat']] + [['transition_seconds' , transition_seconds]])
  new_state2 = dict([[key, item] for [key, item] in light1_state.items() if key in ['on', 'hue', 'bri', 'sat']] + [['transition_seconds' , transition_seconds]])
  # Swap
  controller.alter_lights_state([light1], new_state1)
  controller.alter_lights_state([light2], new_state2)

  # Make the controller push the state to the light
  controller.push_state()



###############################
# Simple commands             #
# to be used in a single call #
###############################

def cmd_off(controller, lights = None):
  """Turns off lights"""
  command = {'on' : False} #, 'transition_seconds' : transtime}
  controller.alter_lights_state(lights, command)
  # controller.alter_lights_state(controller.lights, command)
  controller.push_state()

def cmd_on(controller, lights = None, transtime = 1):
  """Turns off lights"""
  command = {'on' : True, 'transition_seconds' : transtime}
  controller.alter_lights_state(lights, command)
  controller.push_state()

def cmd_dim(controller, lights = None, transtime = 1, bri_factor = 0.8):
  """ Dim lights"""
  old_brightness = {light:state['bri'] for light, state in controller.state.items() if light in lights}
  for light in lights:
    # Multiply with 0.8
    command = {'bri' :  int(controller.state[light]['bri'] * bri_factor),
              'transition_seconds' : transtime}
    print('Light "{}" set to {}'.format(light, sorted(command.items())))
    controller.alter_lights_state([light], command)
  controller.push_state()

def cmd_turn_on_random(controller, lights = None, hue_range = HUE_RANGE, sat_range = [150,240], bri_range = [220,255], ignore_on = False, transtime = 1):
  """Turns lights on to a random state if they were not on already"""
  current_state = controller.state
  for light in lights:
    if ignore_on or not current_state[light]['on']: #Light is currently off or its state is to be ignored
      command = {
        'on' : True,
        'bri' : rng.randint(*bri_range),
        'sat' : rng.randint(*sat_range),
        'hue' : rng.randint(*hue_range),
        'transition_seconds' : transtime
        }
      controller.alter_lights_state([light], command)
      print('Light "{}" set to {}'.format(light, sorted(command.items())))
    else:
      print('Light "{}" was already on'.format(light))
  controller.push_state()

def cmd_blink_alert(controller):
  old_state = deepcopy(controller.state)
  # Blink
  command = {'on' : True, 'bri' : 255, 'sat' : 255, 'hue' : 50142} #TODO different colours
  controller.alter_lights_state(controller.lights, command)
  controller.push_state()
  # time.sleep(.5)

  #Return to old state
  for light in controller.lights:
    controller.alter_lights_state([light], old_state[light])
  # print(controller.state['Piano']['hue'])
  controller.push_state()



#TODO: phue._reset_bri_after_on

####################
# Argument handler #
####################

def parse_cmd_arguments():
  """ Parse command line arguments"""

  parser = argparse.ArgumentParser(description='Control Philips Hue lights.')
  available_commands = sorted([item for key, item in COMMANDS.items()])
  # Single optional string argument
  parser.add_argument(metavar = 'command',
      dest = 'cmd',
      nargs = "?",
      action="store",
      choices = available_commands,
      type = str,
      default=None,
      help="Run a single simple command and exit. (Choose from: {})".format(', '.join(available_commands)),
    )

  # List of lights argument
  parser.add_argument('-l', '--lights',
      action="store",
      type = str,
      metavar = 'light',
      nargs = '+',
      default=[],
      help="specify lights",
    )

  # Duration for effects
  parser.add_argument('-d', '--duration',
      action="store",
      type = int,
      metavar = 'duration',
      # nargs = 1,
      default=None,
      help="Effect duration in minutes for commands: " + ', '.join(COMMANDS_DURATION),
    )

  # Transition time
  parser.add_argument('-t', '--transtime',
      action="store",
      type = int,
      metavar = 'transition',
      # nargs = 1,
      default=1,
      help="Transition time in seconds",
    )

  # Wait time in seconds
  parser.add_argument('-w', '--wait',
      action="store",
      type = int,
      metavar = 'wait',
      # nargs = 1,
      default=0,
      help="Wait time before starting in seconds",
    )

  # Random option flags
  parser.add_argument('-o', '--options',
      action="store",
      type = str,
      metavar = 'opt',
      nargs = '+',
      default=[],
      help="Various options for various commands.",
      # 'state': Print state
      # 'ignore_on': Option for random_cols. Ignore the fact that a light is on already and overwrite.
    )

    # Random option flags
  parser.add_argument('-j', '--json',
      action="store",
      type = str,
      metavar = 'opt',
      nargs = '?',
      default=None,
      help="Json parameters for fine tuning the commands: " + ', '.join(COMMANDS_JSON),
    )

  # Bridge ip address
  parser.add_argument('-i', '--ip',
      action="store",
      type = str,
      metavar = 'ip-address',
      nargs = 1,
      default=None,
      help="IP address for the bridge.",
    )

  # Bridge user name
  parser.add_argument('-u', '--uname',
      action="store",
      type = str,
      metavar = 'user name',
      nargs = 1,
      default=None,
      help="IP address for the bridge.",
    )


  return parser.parse_args()

###############
# Main access #
###############

if __name__ == '__main__':

  # Manual override of cmd line options for testing
  if len(sys.argv) ==1 :
    # sys.argv += '--help'.split(' ')
    # sys.argv += 'off -l Piano -o state -w 2'.split(' ')
    # sys.argv += 'on -l Piano -o state'.split(' ')
    # sys.argv += 'slide -l Piano -t 1 -j "{\'speed\':10000}"'.split(' ')
    # sys.argv += 'default'.split(' ')
    # sys.argv += 'off --lights Ceiling'.split(' ')
    # sys.argv += 'blink_alert'.split(' ')
    # sys.argv += 'random_col --lights Piano Couch'.split(' ')
    # sys.argv += 'random_col --lights Doorbank Mannetje Plant --options ignore_on'.split(' ')
    pass

  #
  # Parse arguments
  #
  args = parse_cmd_arguments()


  #parse the json option if present
  json_parameters = {}
  if args.json:
    json_parameters = json.loads(args.json.replace('\'', '"'))

  #
  # Retrieve ip and set up the controller
  # Set-up the controller
  #
  bridge_ip     = BRIDGES['Tom']['ip']    if not args.ip    else args.ip
  bridge_uname  = BRIDGES['Tom']['uname'] if not args.uname else args.uname
  controller = Light_controller()
  controller.set_bridge(bridge_ip = bridge_ip, bridge_uname = bridge_uname)

  #
  # if no lights specified, apply effects to all
  #
  if not args.lights:
    args.lights = controller.lights

  #
  # Wait if specified
  #
  if args.wait >0:
    time.sleep(args.wait)

  #
  # Run command
  #
  if args.cmd == None:
    print('default, do nothing')
    # TODO: Interactive shell?
    exit()

  if args.cmd == COMMANDS['state'] or 'state' in args.options:
    # Print start state
    print('Start state: ')
    print(controller.print_state())
    # exit()

  if args.cmd == COMMANDS['off']:
    # Turn off everything
    cmd_off(controller, args.lights)
    exit()

  if args.cmd == COMMANDS['on']:
    # Turn off everything
    cmd_on(controller, args.lights, transtime = args.transtime)
    exit()

  if args.cmd == COMMANDS['dim']:
    # Flash all lights once
    cmd_dim(controller, args.lights, transtime = args.transtime)
    exit()

  if args.cmd == COMMANDS['random_col']:
    # Random colour to specified lights.
    # Options: 'ignore_on' to ignore the on-state of lights. (Thus overriding them with a new random colour)
    cmd_turn_on_random(controller, args.lights, ignore_on = ('ignore_on' in args.options or 'ignore_on' in json_parameters), transtime = args.transtime)
    exit()

  if args.cmd == COMMANDS['blink_alert']:
    # Flash all lights once
    cmd_blink_alert(controller)
    exit()

  if args.cmd == COMMANDS['register']:
    bridge = phue.Bridge(bridge_ip)
    bridge.connect()
    exit()

  # Timed effect
  # example - breathe Piano for one minute:
  #     hue.py breathe --lights Piano --json "{'bri_range':[120,200], 'interval':15}" --duration 60
  if args.cmd == COMMANDS['breathe']:
    brightness_range = json_parameters.get('bri_range', [100, 180])
    duration = time_delta(minutes = args.duration) if args.duration else None

    print(args)
    repeater(interval = args.transtime, endtime = duration, message = 'breathe ' + ', '.join(args.lights) )(effect_breathe)(
        controller,
        lights = args.lights,
        brightness_range= brightness_range ,
        transition_seconds = args.transtime
    )
    exit()

  if args.cmd == COMMANDS['slide']:
    speed = json_parameters.get('speed', 1000)
    duration = time_delta(minutes = args.duration) if args.duration else None

    print(args)
    repeater(interval = args.transtime, endtime = duration, message = 'slide ' + ', '.join(args.lights) )(effect_hue_slide)(
        controller,
        lights = args.lights,
        transition_seconds = args.transtime,
        speed = speed
    )
    exit()

