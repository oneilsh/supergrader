#!/usr/bin/env python
import os
import json
import sys
import argparse
import subprocess
import toml
import io
import re
import pipes
import random
import time

script_path = os.path.dirname(os.path.realpath(__file__))

# This script isn't really for direct use. It assumes a lot of environment setup
# provided by supergrader.py (including the tmux keybinding to actually run this script)


# it could also use some cleanup, it's pretty fragile at the moment.

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--dir', dest = 'dir', help = "Go to this folder and execute the panel commands.")
  parser.add_argument('-n', '--next', dest = 'next', action = 'store_true', help = "Go to the next folder in the list.")
  parser.add_argument('-p', '--previous', dest = 'previous', action = 'store_true', help = "Go to the previous folder in the list.")
  parser.add_argument('-m', '--use_macro', dest = 'use_macro', help = "Tell tmux to insert a macro string (or macroset) by name.")
  parser.add_argument('-t', '--use_macro_target', nargs=2, metavar = ('macro_name', 'macro_panel'), help = "Target a macro to a particular panel number.")
  parser.add_argument('--show_interactive_help', dest = 'show_interactive_help', action = 'store_true', help = "Open some help in less, don't do anything else.")
  
  return parser.parse_args()
  

args = parse_args()

def session_exists():
  session_name = "SuperGrader"
  try:
    check_result = subprocess.check_output("tmux has-session -t " + session_name, shell = True)
  except subprocess.CalledProcessError as res:
      return False
  return True



if args.show_interactive_help: 
  if session_exists():
    subprocess.check_output("tmux select-window -t SuperGrader:control", shell = True)
    windowsize = subpocess.check_output("tmux display -p '#{pane_width}'", shell = True).strip()
    subprocess.check_output("tmux send 'cat " + script_path + "/supergrader_help.txt | fold -s -w " + windowsize + " | less && tmux select-window -t SuperGrader:panels'", shell = True)
    subprocess.check_output("tmux send Enter", shell = True)
  else:
    sys.stderr.write("Please don't run supergrader_utility.py directly. It's not meant for that. (If you used ^b h inside SuperGrader, this is an error that shouldn't happen.")
    exit(1)


# returns a string or a dict; if a string, it's the macro to run.
# if a dict, it's a set of panel numbers as keys and macros to run in those
# panels as values (for macrosets)
def read_macro(desired):
  if os.environ.get("MACROFILE", "NA") != "NA":       # if there's a value and it's not NA
    toml_dict = toml.loads(io.open(os.environ["MACROFILE"], "r").read())

    macros = toml_dict.get("macros", None)
    if macros:
      for name in macros:
        if name == desired:
          val = macros[name]
          # if the macro is a list of macros, select one at random.
          if val.__class__.__name__ == 'list':
            val = random.choice(val)            
          val = re.subn(r"\t", r"\\t", val, 0)[0]
          val = re.subn(r"\n", r"\\n", val, 0)[0]
          val = re.subn(r"'", r"'\''", val, 0)[0]
          val = re.subn(r'"', r'"\""', val, 0)[0]
          
          return val

    macrosets = toml_dict.get("macrosets", None)
    if macrosets:
      for name in macrosets:
        if name == desired:
          val = macrosets[name]
          per_panel_macros = val.split(";")

          ret_dict = dict()
          for per_panel_macro in per_panel_macros:
            macro, panel = [part.strip() for part in per_panel_macro.split("->")]
            ret_dict[panel] = macro
          return ret_dict
  
  else:
    subprocess.check_output("tmux display-message 'No macros file specified for session, cannot run macros. Call supergrader with -M option.", shell = True)





if args.use_macro:
  macro_val = read_macro(args.use_macro)
  if macro_val.__class__.__name__ == 'dict':

    quit()

  macro_res = subprocess.check_output('/bin/echo -n -e "' + macro_val + '"', shell = True)
  lines = macro_res.split("\n")
  for line in lines:
    special_split = line.split("@@@")   # sleep 5\n@@@Ctrl-C@@@ echo done\n -> ["sleep 5\n", "Ctrl-C", "echo done\n"]
    
    for i in range(0,len(special_split)):
      tosend = special_split[i]
      tmux_control = i % 2 == 1

      if tmux_control:
        if tosend.startswith("WAIT-"):
          secs = re.subn("WAIT-", "", tosend)[0]
          time.sleep(int(secs))
          continue

      if tmux_control:
        cmd = "tmux send-keys '" + tosend + "'"
        subprocess.check_output(cmd, shell = True)

      else:
        cmd = "tmux send-keys -l '" + tosend + "'"
        subprocess.check_output(cmd, shell = True)
        
    cmd = "tmux send-keys Enter"
    subprocess.check_output(cmd, shell = True)

  quit()

if args.dir == None and args.next == False and args.previous == False:
  subprocess.check_output("tmux display-message 'supergrader_utility.py called with no valid options. This shouldnt happen. WHAT DID YOU DO?", shell = True)
  sys.exit(1)

#########################################
### If we get here, we're moving to a different folder (or at least attempting to). 

sg_info = subprocess.check_output("tmux showenv SG_INFO", shell = True).strip()
sg_dict = json.loads(sg_info[8:])   # strip off "SG_DICT=" 
dirs = sg_dict["dirs"]
panels = sg_dict["panels"]
currentdir = sg_dict["currentdir"]
basedir = sg_dict["basedir"]
filter_command = None
if "filter_command" in sg_dict:
  filter_command = sg_dict["filter_command"]



## first, see if they specified something with -d
foldername = None
if args.dir:
  if os.path.join(basedir, args.dir) in dirs: # are they specifying just a folder name?
    foldername = os.path.join(basedir, args.dir)
  elif args.dir in dirs:             # or a full or relative path?
    foldername = args.dir
  else:
    subprocess.check_output("tmux display-message 'No known folder " + args.dir + " to go to.'", shell = True)
    sys.exit(1)


# otherwise, we'll process next and previous
# but if the currentdir is NA, then we just set it to the first entry
# (this should probably always be set to an entry in dirs by supergrader.py?)
if currentdir == 'NA' and foldername == None:
  # if currentdir is nothing (and we didn't select one with -d), 
  # we just set it to the first one in the list no matter what
  foldername = dirs[0]

elif args.next == True:
  currentdir_index = dirs.index(currentdir)
  if currentdir_index + 1 < len(dirs):
    foldername = dirs[currentdir_index + 1]
  else:
    subprocess.check_output("tmux display-message 'No next folder.'", shell = True)
    sys.exit(0)

elif args.previous == True:
  currentdir_index = dirs.index(currentdir)
  if currentdir_index - 1 >= 0:
    foldername = dirs[currentdir_index - 1]

  else:
    subprocess.check_output("tmux display-message 'No previous folder.'", shell = True)
    sys.exit(0)

# update environment for tracking
sg_dict["currentdir"] = foldername
cmd = "tmux setenv SG_INFO '" + json.dumps(sg_dict) + "'"
subprocess.check_output(cmd, shell = True)


## Setup lower-right info
gotofolder_index = dirs.index(foldername)

basename = os.path.basename(foldername)
fullname = subprocess.check_output("finger -l " + basename + " | grep Name | sed -r 's/^.+Name: //g'", shell = True)
fullname = fullname.replace("'", r"'\''")   # escape single quotes (e.g. in O'Neil, actually doing a ' => '\'' replacement)
basename = str(1 + gotofolder_index) + "/" + str(len(dirs)) + " " + basename

if fullname != "":
  basename = basename + " (" + fullname + ")"

basename = basename + " "
subprocess.check_output("tmux set -g status-right '" + basename + "'", shell = True)


fdate = '"' + subprocess.check_output("date +%Y-%m-%d_%H:%M:%S", shell = True).strip() + '"'
hdate = '"' + subprocess.check_output("date '+%b %d, %Y @ %I:%M%p'", shell = True).strip() + '"'
add_setenv_cmd = """  '/bin/test $?BASH_VERSION = 0 || eval ' "'" 'setenv ( ) {export $1=$2}' "'" Enter  """

# set things up for the control panel to use things for macro 
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + add_setenv_cmd, shell = True)    
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " 'setenv DIR " + os.path.basename(foldername) + "'", shell = True)
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " Enter", shell = True)
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " 'setenv HDATE " + hdate + "'", shell = True)
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " Enter", shell = True)
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " 'setenv FDATE " + fdate + "'", shell = True)
subprocess.check_output("tmux send-keys -t SuperGrader:control.0 " + " Enter", shell = True)

# update the panels and refresh the display
for panel in panels:
  type = panel["type"]
  command = panel["command"]
  index = panel["index"]
  
  if type == "dynamic":  # need to update it
    subprocess.check_output("tmux respawn-pane -t SuperGrader:panels." + index + " -k -c '" + foldername + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " " + add_setenv_cmd, shell = True)    
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " 'setenv DIR " + os.path.basename(foldername) + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " Enter", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " 'setenv HDATE " + hdate + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " Enter", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " 'setenv FDATE " + fdate + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " Enter", shell = True)

    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " C-l" , shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " '" + command + "'", shell = True)
    subprocess.check_output("tmux send-keys -t SuperGrader:panels." + index + " Enter", shell = True)


subprocess.check_output("tmux select-window -t SuperGrader:panels", shell = True)





