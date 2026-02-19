title: /YouTube/
-
^(play | pause)$ : key(space)
louder sound track: key(up)
quieter sound track:key(down)
seek forward: key(right)
seek backward: key(left)
seek forward ten seconds: key(l)
seek backward ten seconds: key(j)
next frame: key(,)
last frame: key(.)
youtube <user.number_key>: key(user.number_key)
seek beginning: key(home)
seek ending: key(end)
play back slower: key(<)
play back faster: key(>)
next video: key(N)
last video: key(P)

sub titles: key(c)
increase font size: key(+)
decrease font size: key(-)
text opacity: key(o)
window opacity: key(w)


#global shortcuts
#These keyboard shortcuts can be used when the video player either has or doesn't have the focus, but they are inactive when you are typing some text.

^(play | pause)$: key(k)
^toggle mute$: key(m)
^toggle full screen$: key(f)
^toggle theater mode$: key(t)
^toggle mini player mode$: key(i)

# tutorial series (9 videos, two hours total) on how this file was created is here:  https://youtube.com/playlist?list=PLOChdnCXLga4fduRCuaQwEc_8BitX3PqE

# This script, specifically the youtube <user.number_key> command, depends on the knausj repository being present in order to be able to use the <user.number_key capture>

# Many people using this script will also be using Vimium.  This script will not work out of the box with vimium. To make it work with vimium, you have to deactivate vimium so that the vimium keyboard shortcuts stop working and the keyboard shortcuts for this website start working.  The easiet way to do this is to put vimium in insert mode by pressing the 'i' key (or saying 'sit' in Talon, if you are using the default phonetic alphabet that comes with the knausj repository.  Putting vimium in insert mode will allow all the keybaord shortcuts for whatever webpage you are on to trigger instead of being overridden by vimium. This means that every key except for 'i' and 'escape' will work. 

# I don't need to implement escape, because the word escape already presses the escape key. also, if you are using vimium, the escape key won't work because it conflicts with vimium's mode switcher.  also, toggle mini's screen mode will not work when minium is active, because because 'I' is used to put vimium in insert mode.  Say It is necessary to put vimium in  insert  mode  because putting vim um an insert mode turns off most of the keys that conflict with youtube's hot keys and then you can use youtube's hot keys to control youtube. 

 