



### Install and requirements


The tmux utility (version >= 2.6) and python are required. For install, place `supergrader.py`, `supergrader_utility.py`, `supergrader_help.txt`, and `supergrader_tmux.conf` in the same location, somewhere accessible by `$PATH`.


### Quick Reference (details below)


Since SuperGrader is a wrapper around tmux, all tmux commands and configuration are available. 

Note that in tmux `C-b h` is taken to mean "Control-b followed by h", whereas this document uses `^b h` to mean the same thing. The default "prefix" (command-activator) in tmux is `^b`, so `^b h` activates whatever tmux command is bound to the `h` key. SuperGrader also adds `^a` as a prefix, so as to match the behavior of GNU Screen.

Example usage: 

```
supergrader.py --dynamic-panel 'ls' --dynamic-panel 'nano answer.txt' --static-panel 'nano grades.txt' --dirs /ACTF/home
```

The above iterates over the folders in `/ACTF/home`, and opens three panels: one that runs `ls` in each, one that runs `cat answer.txt` in each, and one which runs `nano grades.txt` from the current working directory, and does not iterate over folders with the other panels.

SuperGrader interactive commands:

`^b n` (or `^a n`): Go to next folder in the list and re-execute the dynamic panel commands. Note that this kills the current set of dynamic panels (so be sure to save any changes if you edit files with them)

`^b p` (or `^a p`): Same as above, but go to previous folder in list.

`^b x` (or `^a x`): Exit SuperGrader, closing the session.

`^b d` (or `^a d`): Detach from SuperGrader, allowing later re-attachment.

`^b f` (or `^a f`): Prompt for a folder name to jump to, rather than using next or previous.


### About


SuperGrader is a set of tmux scripts that help with automating executing a handful of commands within a series of subfolders of a common folder; the specific use case is for grading student folders of the form:

```
some_dir/
  student_1/
  student_2/
  student_3/
```

Where each student folder may contain subfolders, files, etc. that we want to run specific commands for. For example, suppose each student has a `hw1.py` script, and to grade this file we need to 1) run `python hw1.py` to review the output, 2) run `nano hw1.py` or (`vim hw1.py` etc.) to review the code and add comments, and 3) run `nano allgrades.txt` to enter grades into a gradebook, but this command should not be run for each student folder. This can be accomplished with:

```
supergrader.py --dynamic-panel 'python hw1.py' --dynamic-panel 'nano hw1.py' --static-panel 'nano allgrades.txt' --dirs some_dir
```

or, in short form:

```
supergrader.py -p 'python hw1.py' -p 'nano hw1.py' -s 'nano allgrades.txt' -d some_dir
```

Upon opening, the static panel will run its command, and the dynamic panels will change to the `student_1` directory and run their respective commands. 

The grader can then use `^b n` (or `^a n`) to move the dynamic panels to the next folder (student_2) and re-run their commands. Note that when doing so, any processes currently running in the dynamic panels are killed, so in this example we'd want to save any edits we made in the 'nano hw1.py' panl before entering `^b n`.



### Exit Codes


The basic usage of SuperGrader is superified by understanding and using command-line exit codes. Although not shown by default, each command run returns a "success" exit code (0) or an "error" exit code (not 0). These exit codes can be used to control series of commands. Suppose, for example, that we want a panel to first `cd hw1`, and then run `python hw1.py`. This could be accomplished with

```
--dynamic-panel 'cd hw1; python hw1.py'
```

However, if no hw1 folder exists, the first command will return an error code, but the second command will still try and run. Instead, we can use the `&&` to only execute the latter if the first returned a success code:

```
--dynamic-panel 'cd hw1 && python hw1.py'
```

This will cause `python hw1.py` to only execute if `cd hw1` successfully executed first. By the way, to see the exit code of a previous command (for testing purposes), try

```
echo $?
```


It may be that some students named their folders `HW1` instead of `hw1`, in which case we want to execute `cd hw1`, and if that fails, try `cd HW1`, and if either of those succeeded, run `python hw1.py`. This syntax accomplishes that:

```
--dynamic-panel 'cd hw1 || cd HW1 && python hw1.py'
```


[Warning: by default on CGRB servers, `cd` is aliased to `cd !*; pwd`, so every `cd` also executes a `pwd`, making the result look successful even if the folder is not found. You may wish to add 

```
unalias cd
alias cd 'cd \!* && pwd' 
```

to your `.cshrc`. Note that this also only works if you have permissions for the folders in question: on the ACTF there is currently a permissions bug where you may need to `newgrp` before running SuperGrader.]

These features may depend on the shell being used and its configuration. In bash, it is possible to logically group commands, though the syntax is fragile (proper whitespace required, and semicolon required at the end of each group's command set):

```
--dynamic-panel '{ cd hw1 || cd HW1; } && { python hw1.py || python HW1.py; }'
```

### Features

Commands can reference the shell variable DIR, which contains the specific folder name being graded. For example, to edit a file called `grade_student_1.txt` inside of `student_1/`, and `grade_student_2.txt` inside of `student_2/`, try:

```
--dynamic-panel 'nano grade_$DIR.txt'
```


The current `$DIR` is shown in the lower-right. If `$DIR` also happens to be a username, then the person's full name will also be shown as reported by `finger $DIR`. A progress indicator (folder number / total number of folders) is also shown in the lower-right before the folder name.

If your terminal is setup for it (most are by default), you can navigate between panels and resaize panels with the mouse. Alternatively, you can use `^b` (or `^a`) followed by an arrow key to navigate.

The `--filter-command` (or `-f`) option allows to filter folders based on the exit code of the supplied command, run within each folder. For example, to only consider folders where `ls hw1` is successful, one could add a

```
--filter-command 'ls hw1'
```

Perhaps we've instructed students to add a line `# grade_please` to one of their .py files, to only grade those would could

```
--filter-command 'grep grade_please hw1/*.py'
```

Or, perhaps we have a `gradebook.txt` file, and we only want to grade those where we don't find the directory name in `gradebook.txt` (`!` negates exit codes):

```
--filter-command '! grep $DIR gradebook.txt'
```

Pipes work too; here we filter based on those that don't have a result after grepping through `gradebook.txt` and then grepping for `hw1` (i.e., we only want to grade those that we don't have a grade for hw1):

```
--filter-command '! grep $DIR gradebook.txt | grep hw1'
```



### Future ideas


The backend script (supergrader_utility.py) needs refactoring to be more multipurpose without so much logic.

I'd like to be able to define "macros", e.g. so that `^b m` prompts the user for a macro name (e.g. "missing_semicolon") and then a message associated with the name ("You are missing a semicolon; -1 point."). Then perhaps a `^b M` would prompt for a name (e.g. "missing_semicolon") and then send the corresponding message to the panel. This would help with the common situation where many students make a similar mistake.

