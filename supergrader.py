#!/usr/bin/env python
import argparse
import subprocess
import os
import time
import json
import sys


def parse_args():
  parser = argparse.ArgumentParser("SuperGrader. For details run `supergrader.py` then Control-b h")
  parser.add_argument('-p', '--dynamic-panel', dest = 'dynamic_panel_cmds', action = 'append', help = "Create a pane running these commands for each folder.")
  parser.add_argument('-s', '--static-panel', dest = 'static_panel_cmds',action = 'append', help = "Create a pane running this command, don't update the pane between folders.")
  parser.add_argument('-d', '--dirs', dest = 'directory', default = os.getcwd(), help = "Look in this folder for folders to grade. (Default: current working directory.)")
  parser.add_argument('-f', '--filter-command', dest = 'filter_command', help = "Only process folders when this this command, run in the folder, exits with a success code.")
  
  return parser.parse_args()
  
args = parse_args()




def get_subdirs(dir, filter_command = None):
  alldirs = [os.path.join(dir, o) for o in os.listdir(dir) if os.path.isdir(os.path.join(dir,o))]
  if not filter_command:
    return alldirs
    
  filtered = []
  for dir in alldirs:
    try:
      cmd = "DIR=" + os.path.basename(dir) + "; " + filter_command
      sys.stderr.write("Checking filter in " + dir + " with `" + cmd + "`\n")
      subprocess.check_output(cmd, shell = True, cwd = dir)
      filtered.append(dir)
    except:
      pass

  return filtered


# creates a session with the given name; if it exists, prompts the user to attach or kill it before continuing
def create_session(panelcmds):
  session_name = "SuperGrader"
  try: # if it already exists...
    check_result = subprocess.check_output("tmux has-session -t " + session_name, shell = True)
    result = raw_input("A session exists with that name. Attach (a) or kill (k)? ")
    if result == "a":
      subprocess.check_output("tmux select-window -t SuperGrader:panels", shell = True)
      subprocess.check_output("tmux attach-session -d -t SuperGrader", shell = True)
      exit(0)
    else:
      subprocess.check_output("tmux kill-session -t SuperGrader", shell = True)
      subprocess.check_output("tmux new-session -d -s SuperGrader", shell = True)
      subprocess.check_output("tmux new-window -n control ", shell = True)
      subprocess.check_output("tmux new-window -n panels ", shell = True)
     
  except subprocess.CalledProcessError as res:
    print(res)
    subprocess.check_output("tmux new-session -d -s " + session_name, shell = True)
    subprocess.check_output("tmux new-window -n control ", shell = True)
    subprocess.check_output("tmux new-window -n panels ", shell = True)


  subprocess.check_output("tmux select-window -t panels ", shell = True)
  
  for i in range(0, len(panelcmds) - 1):
    subprocess.check_output("tmux split-window -v", shell = True)
    subprocess.check_output("tmux select-layout tiled ", shell = True)

  subprocess.check_output("tmux select-window -t control ", shell = True)



dynamic_panel_commands = args.dynamic_panel_cmds
static_panel_commands = args.static_panel_cmds

if dynamic_panel_commands == None:
  dynamic_panel_commands = []

if static_panel_commands == None:
  static_panel_commands = []

dirs_list = get_subdirs(args.directory, args.filter_command)

create_session(dynamic_panel_commands + static_panel_commands)



panels = []
for i in range(0, len(dynamic_panel_commands)):
  command = dynamic_panel_commands[i]
  type = "dynamic"
  panels.append({"type": type, "command": command , "index": str(len(panels))})

for i in range(0, len(static_panel_commands)):
  command = static_panel_commands[i]
  type = "static"
  panels.append({"type": type, "command": command, "index": str(len(panels))})


sg_dict = {"panels": panels, "dirs": dirs_list, "currentdir": "NA", "basedir": args.directory}
if args.filter_command:
  sg_dict["filter_command"] = args.filter_command

for panel in panels:
  type = panel["type"]
  command = panel["command"]
  index = panel["index"]
  
  if type == "static": # run the static commands once, during supergrader setup
    subprocess.check_output("tmux respawn-pane -t SuperGrader:panels." + index + " -k ", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " '" + command + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " Enter", shell = True)


cmd = "tmux setenv SG_INFO '" + json.dumps(sg_dict) + "'"
subprocess.check_output(cmd, shell = True)

subprocess.check_output("tmux select-window -t SuperGrader:panels", shell = True)
subprocess.check_output("tmux send -t SuperGrader:control 'supergrader_utility.py -n'", shell = True)
subprocess.check_output("tmux send -t SuperGrader:control Enter", shell = True)

script_path = os.path.dirname(os.path.realpath(__file__))
subprocess.check_output("tmux source-file " + os.path.join(script_path, "supergrader_tmux.conf"), shell = True)



cmd = "tmux -2 attach "
subprocess.check_output(cmd, shell = True)





