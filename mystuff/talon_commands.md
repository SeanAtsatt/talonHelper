


# dictation mode

| Command | Result |
| :---- | :---- |
| **press** | key("{keys}") |
|  | auto\_insert(prose) |
| **new line** | "\\n" |
| **new paragraph** | "\\n\\n" |
| **cap** | result \= user.formatted\_text(word, "CAPITALIZE\_FIRST\_WORD") auto\_insert(result) \# Navigation |
| **go up (line|lines)** | edit.up() repeat(number\_small \- 1\) |
| **go down (line|lines)** | edit.down() repeat(number\_small \- 1\) |
| **go left (word|words)** | edit.word\_left() repeat(number\_small \- 1\) |
| **go right (word|words)** | edit.word\_right() repeat(number\_small \- 1\) |
| **go line start** | edit.line\_start() |
| **go line end** | edit.line\_end() |
| **select left (word|words)** | edit.extend\_word\_left() repeat(number\_small \- 1\) |
| **select right (word|words)** | edit.extend\_word\_right() repeat(number\_small \- 1\) |
| **select left (character|characters)** | edit.extend\_left() repeat(number\_small \- 1\) |
| **select right (character|characters)** | edit.extend\_right() repeat(number\_small \- 1\) |
| **clear left (word|words)** | edit.extend\_word\_left() repeat(number\_small \- 1\) edit.delete() |
| **clear right (word|words)** | edit.extend\_word\_right() repeat(number\_small \- 1\) edit.delete() |
| **clear left (character|characters)** | edit.extend\_left() repeat(number\_small \- 1\) edit.delete() |
| **clear right (character|characters)** | edit.extend\_right() repeat(number\_small \- 1\) edit.delete() \# Formatting |
| **formatted** | user.dictation\_insert\_raw(format\_text) |
| **format selection** | user.formatters\_reformat\_selection(formatters) \# Corrections |
| **scratch that** | user.clear\_last\_phrase() |
| **scratch selection** | edit.delete() |
| **select that** | user.select\_last\_phrase() |
| **spell that** | auto\_insert(letters) |
| **spell that** | result \= user.formatted\_text(letters, formatters) user.dictation\_insert\_raw(result) \# Escape, type things that would otherwise be commands |
| **escape** | auto\_insert(user.text) |

# 

# modifier\_key

| Command | Result |
| :---- | :---- |
| alt | alt |
| control | ctrl |
| shift | shift |
| super | super |

# Special\_key

| Command | Result |
| :---- | :---- |
| **end** | end |
| **enter** | enter |
| **escape** | escape |
| **home** | home |
| **insert** | insert |
| **pagedown** | pagedown |
| **pageup** | pageup |
| **space** | space |
| **tab** | tab |
| **delete** | backspace |
| **forward delete** | delete |
| **page up** | pageup |
| **page down** | pagedown |
| **menu key** | menu |
| **print screen** | printscr |

# 

# symbol\_key

| Command | Result |
| :---- | :---- |
| **dot** | . |
| **point** | . |
| **quote** |  |
| **apostrophe** |  |
| **L square** | \[ |
| **left square** | \[ |
| **square** | \[ |
| **R square** | \] |
| **right square** | \] |
| **slash** | / |
| **backslash** | \\ |
| **minus** | \- |
| **dash** | \- |
| **equals** | \= |
| **plus** | \+ |
| **tilde** | \~ |
| **bang** | \! |
| **down score** | \_ |
| **under score** | \_ |
| **paren** | ( |
| **L paren** | ( |
| **left paren** | ( |
| **R paren** | ) |
| **right paren** | ) |
| **brace** | { |
| **left brace** | { |
| **R brace** | } |
| **right brace** | } |
| **angle** | \< |
| **left angle** | \< |
| **less than** | \< |
| **rangle** | \> |
| **R angle** | \> |
| **right angle** | \> |
| **greater than** | \> |
| **star** | \* |
| **hash** | \# |
| **percent** | % |
| **caret** | ^ |
| **amper** | & |
| **pipe** | | |
| **dubquote** | " |
| **double quote** | " |
| **empty dub string** | “” |
| **dollar** | $ |
| **pound** | £ |
| **\`** | \` |
| **,** | , |
| **back tick** | \` |
| **grave** | \` |
| **comma** | , |
| **period** | . |
| **full stop** | . |
| **semicolon** | ; |
| **colon** | : |
| **forward slash** | 8 |
| **question mark** | ? |
| **exclamation mark** | \! |
| **exclamation point** | \! |
| **asterisk** | \* |
| **hash sign** | \# |
| **number sign** | \# |
| **percent sign** | % |
| **at sign** | @ |
| **and sign** | & |
| **ampersand** | & |
| **dollar sign** | $ |
| **pound sign** | £ |

# arrow\_key

| Command | Result |
| :---- | :---- |
| **down** | down |
| **left** | left |
| **right** | right |
| **up** | up |

# punctuation

| Command | Result |
| :---- | :---- |
| **\`** | \` |
| **,** | , |
| **back tick** | \` |
| **grave** | \` |
| **comma** | , |
| **period** | . |
| **full stop** | . |
| **semicolon** | ; |
| **colon** | : |
| **forward slash** | / |
| **question mark** | ? |
| **exclamation mark** | \! |
| **exclamation point** | \! |
| **asterisk** | \* |
| **hash sign** | \# |
| **number sign** | \# |
| **percent sign** | % |
| **at sign** | @ |
| **and sign** | & |
| **ampersand** | & |
| **dollar sign** | $ |
| **pound sign** | £ |

# generic editor

| Commandm | Result |
| :---- | :---- |
| **find it** | edit.find() |
| **next one** | edit.find\_next() |
| **go word left** | edit.word\_left() |
| **go word right** | edit.word\_right() |
| **go left** | edit.left() |
| **go right** | edit.right() |
| **go up** | edit.up() |
| **go down** | edit.down() |
| **go line start** | edit.line\_start() |
| **go line end** | edit.line\_end() |
| **go way left** | edit.line\_start() edit.line\_start() |
| **go way right** | edit.line\_end() |
| **go way down** | edit.file\_end() |
| **go way up** | edit.file\_start() |
| **go bottom** | edit.file\_end() |
| **go top** | edit.file\_start() |
| **go page down** | edit.page\_down() |
| **go page up** | edit.page\_up() \# selecting |
| **select line** | edit.select\_line() |
| **select all** | edit.select\_all() |
| **select left** | edit.extend\_left() |
| **select right** | edit.extend\_right() |
| **select up** | edit.extend\_line\_up() |
| **select down** | edit.extend\_line\_down() |
| **select word** | edit.select\_word() |
| **select word left** | edit.extend\_word\_left() |
| **select word right** | edit.extend\_word\_right() |
| **select way left** | edit.extend\_line\_start() |
| **select way right** | edit.extend\_line\_end() |
| **select way up** | edit.extend\_file\_start() |
| **select way down** | edit.extend\_file\_end() \# editing |
| **indent \[more\]** | edit.indent\_more() |
| **(indent less | out dent)** | edit.indent\_less() \# deleting |
| **clear line** | edit.delete\_line() |
| **clear left** | key(backspace) |
| **clear right** | key(delete) |
| **clear up** | edit.extend\_line\_up() edit.delete() |
| **clear down** | edit.extend\_line\_down() edit.delete() |
| **clear word** | edit.delete\_word() |
| **clear word left** | edit.extend\_word\_left() edit.delete() |
| **clear word right** | edit.extend\_word\_right() edit.delete() |
| **clear way left** | edit.extend\_line\_start() edit.delete() |
| **clear way right** | edit.extend\_line\_end() edit.delete() |
| **clear way up** | edit.extend\_file\_start() edit.delete() |
| **clear way down** | edit.extend\_file\_end() edit.delete() |
| **clear all** | edit.select\_all() edit.delete() \#copy commands |
| **copy all** | edit.select\_all() edit.copy() \#to do: do we want these variants, seem to conflict \# copy left: \# edit.extend\_left() \# edit.copy() \# copy right: \# edit.extend\_right() \# edit.copy() \# copy up: \# edit.extend\_up() \# edit.copy() \# copy down: \# edit.extend\_down() \# edit.copy() |
| **copy word** | edit.select\_word() edit.copy() |
| **copy word left** | edit.extend\_word\_left() edit.copy() |
| **copy word right** | edit.extend\_word\_right() edit.copy() |
| **copy line** | edit.select\_line() edit.copy() \#cut commands |
| **cut all** | edit.select\_all() edit.cut() \#to do: do we want these variants \# cut left: \# edit.select\_all() \# edit.cut() \# cut right: \# edit.select\_all() \# edit.cut() \# cut up: \# edit.select\_all() \# edit.cut() \# cut down: \# edit.select\_all() \# edit.cut() |
| **cut word** | edit.select\_word() edit.cut() |
| **cut word left** | edit.extend\_word\_left() edit.cut() |
| **cut word right** | edit.extend\_word\_right() edit.cut() |
| **cut line** | edit.select\_line() edit.cut() |

# mouse

| Command | Result |
| :---- | :---- |
| **control mouse** | user.mouse\_toggle\_control\_mouse() |
| **zoom mouse** | user.mouse\_toggle\_zoom\_mouse() |
| **camera overlay** | user.mouse\_toggle\_camera\_overlay() |
| **run calibration** | user.mouse\_calibrate() |
| **touch** | mouse\_click(0) \# close the mouse grid if open user.grid\_close() \# End any open drags \# Touch automatically ends left drags so this is for right drags specifically user.mouse\_drag\_end() |
| **righty** | mouse\_click(1) \# close the mouse grid if open user.grid\_close() |
| **midclick** | mouse\_click(2) \# close the mouse grid user.grid\_close() \#see keys.py for modifiers. \#defaults \#command \#control \#option \= alt \#shift \#super \= windows key |
| **touch** | key("{modifiers}:down") mouse\_click(0) key("{modifiers}:up") \# close the mouse grid user.grid\_close() |
| **righty** | key("{modifiers}:down") mouse\_click(1) key("{modifiers}:up") \# close the mouse grid user.grid\_close() |
| **(dubclick | duke)** | mouse\_click() mouse\_click() \# close the mouse grid user.grid\_close() |
| **(tripclick | triplick)** | mouse\_click() mouse\_click() mouse\_click() \# close the mouse grid user.grid\_close() |
| **left drag | drag** | user.mouse\_drag(0) \# close the mouse grid user.grid\_close() |
| **right drag | righty drag** | user.mouse\_drag(1) \# close the mouse grid user.grid\_close() |
| **end drag | drag end** | user.mouse\_drag\_end() |
| **wheel down** | user.mouse\_scroll\_down() |
| **wheel down here** | user.mouse\_move\_center\_active\_window() user.mouse\_scroll\_down() |
| **wheel tiny \[down\]** | mouse\_scroll(20) |
| **wheel tiny \[down\] here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(20) |
| **wheel downer** | user.mouse\_scroll\_down\_continuous() |
|  |  |
| **wheel downer here** | user.mouse\_move\_center\_active\_window() user.mouse\_scroll\_down\_continuous() |
| **wheel up** | user.mouse\_scroll\_up() |
| **wheel up here** | user.mouse\_scroll\_up() |
| **wheel tiny up** | mouse\_scroll(-20) |
| **wheel tiny up here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(-20) |
| **wheel upper** | user.mouse\_scroll\_up\_continuous() |
| **wheel upper here** | user.mouse\_move\_center\_active\_window() user.mouse\_scroll\_up\_continuous() |
| **wheel gaze** | user.mouse\_gaze\_scroll()  |
| **wheel gaze here** | user.mouse\_move\_center\_active\_window() user.mouse\_gaze\_scroll() |
| **wheel stop** | user.mouse\_scroll\_stop() |
| **wheel stop here** | user.mouse\_move\_center\_active\_window() user.mouse\_scroll\_stop() |
| **wheel left** | mouse\_scroll(0, \-40) |
| **wheel left here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(0, \-40) |
| **wheel tiny left** | mouse\_scroll(0, \-20) |
| **wheel tiny left here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(0, \-20) |
| **wheel right** | mouse\_scroll(0,w 40\) |
| **wheel right here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(0, 40\) |
| **wheel tiny right** | mouse\_scroll(0, 20\) |
| **wheel tiny right here** | user.mouse\_move\_center\_active\_window() mouse\_scroll(0, 20\) |
| **curse yes** | user.mouse\_show\_cursor() |
| **curse no** | user.mouse\_hide\_cursor() |
| **copy mouse position** | user.copy\_mouse\_position() |

# Formatters

| Command | Result |
| :---- | :---- |
| **allcaps** | EXAMPLE OF FORMATTING WITH ALLCAPS |
| **alldown** | example of formatting with alldown |
| **camel** | exampleOfFormattingWithCamel |
| **dotted** | example.of.formatting.with.dotted |
| **dubstring** | "example of formatting with dubstring" |
| **dunder** | \_\_example\_\_offormattingwithdunder |
| **hammer** | ExampleOfFormattingWithHammer |
| **kebab** | example-of-formatting-with-kebab |
| **packed** | example::of::formatting::with::packed |
| **padded** | example of formatting with padded |
| **slasher** | /example/of/formatting/with/slasher |
| **smash** | exampleofformattingwithsmash |
| **snake** | example\_of\_formatting\_with\_snake |
| **string** | example of formatting with string' |
| **title** | Example of Formatting With Title |

# generic browser

| Command | Result |
| :---- | :---- |
| **(address bar | go address | go url)** | browser.focus\_address() |
| **(address copy | url copy | copy address | copy url)** | browser.focus\_address() sleep(50ms) edit.copy() |
| **go home** | browser.go\_home() |
| **\[go\] forward** | browser.go\_forward() |
| **go (back | backward)** | browser.go\_back() |
| **go to {user.website}** | browser.go(website) |
| **go private** | browser.open\_private\_window() |
| **bookmark show** | browser.bookmarks() |
| **bookmark bar** | browser.bookmarks\_bar() |
| **bookmark it** | browser.bookmark() |
| **bookmark tabs** | browser.bookmark\_tabs() |
| **(refresh | reload) it** | browser.reload() |
| **(refresh | reload) it hard** | browser.reload\_hard() |
| **show downloads** | browser.show\_downloads() |
| **show extensions** | browser.show\_extensions() |
| **show history** | browser.show\_history() |
| **show cache** | browser.show\_clear\_cache() |
| **dev tools** | browser.toggle\_dev\_tools() |



# history

| Command | Result |
| :---- | :---- |
| **command history** | user.history\_toggle() |
| **command history clear** | user.history\_clear() |
| **command history less** | user.history\_less() |
| **command history more** | user.history\_more() |




# media

| Command | Result |
| :---- | :---- |
| **volume up** | key(volup) |
| **volume down** | key(voldown) |
| **set volume** | user.media\_set\_volume(number) |
| **(volume|media) mute** | key(mute) |
| **\[media\] play next** | key(next) |
| **\[media\] play previous** | key(prev) |
| **media (play | pause)** | user.play\_pause() |

# repeater

| Command | Result |
| :---- | :---- |
|  |  core.repeat\_command(ordinals-1) |
| **times** | core.repeat\_command(number\_small-1) |
| **(repeat that|twice)** | core.repeat\_command(1) |
| **repeat that \[times\]** | core.repeat\_command(number\_small) |

# screens

| Command | Result |
| :---- | :---- |
| **screen numbers** | user.screens\_show\_numbering() |

# **Window management**

| Command | Result |
| :---- | :---- |
| window (new|open) | 4 |
| window next | app.window\_next() |
| window last | app.window\_previous() |
| window close | app.window\_close() |
| focus | user.switcher\_focus(running\_applications) |
| running list | user.switcher\_toggle\_running() |
| launch | user.switcher\_launch(launch\_applications) |
| snap full | Snap window to full screen |
| snap | user.snap\_window(window\_snap\_position) |
| snap next \[screen\] | user.move\_window\_next\_screen() |
| snap last \[screen\] | user.move\_window\_previous\_screen() |
| snap screen | user.move\_window\_to\_screen(number) |
| snap | user.snap\_app(running\_applications, window\_snap\_position) |
| snap \[screen\] | user.move\_app\_to\_screen(running\_applications, number) |

# 

# screenshot

| Command | Result |
| :---- | :---- |
| **grab screen** | user.screenshot() |
| **grab screen** | user.screenshot(number\_small) |
| **grab window** | user.screenshot\_window() |
| **grab selection** | user.screenshot\_selection() |
| **grab screen clip** | user.screenshot\_clipboard() |
| **grab screen clip** | user.screenshot\_clipboard(number\_small) |
| **grab window clip** | user.screenshot\_window\_clipboard() |


# standard

| Command | Result |
| :---- | :---- |
| **zoom in** | edit.zoom\_in() |
| **zoom out** | edit.zoom\_out() |
| **scroll up** | edit.page\_up() |
| **scroll down** | edit.page\_down() |
| **copy that** | edit.copy() |
| **cut that** | edit.cut() |
| **paste that** | edit.paste() |
| **undo that** | edit.undo() |
| **redo that** | edit.redo() |
| **paste match** | edit.paste\_match\_style() |
| **file save** | edit.save() |
| **wipe** | key(backspace) |
| **(pad | padding)** | insert(" ") key(left) |
| **slap** | edit.line\_insert\_down() |

# tabs

| Command | Result |
| :---- | :---- |
| **tab (open | new)** | app.tab\_open() |
| **tab (last | previous)** | app.tab\_previous() |
| **tab next** | app.tab\_next() |
| **tab close** | user.tab\_close\_wrapper() |
| **tab (reopen|restore)** | app.tab\_reopen() |
| **go tab** | user.tab\_jump(number) |
| **go tab final** | user.tab\_final() |


#         homophones

| Command | Result |
| :---- | :---- |
| **phones** | user.homophones\_show(homophones\_canonical) |
| **phones that** | user.homophones\_show\_selection() |
| **phones force** | user.homophones\_force\_show(homophones\_canonical) |
| **phones force** | user.homophones\_force\_show\_selection() |
| **phones hide** | user.homophones\_hide() |
| **phones word** | edit.select\_word() user.homophones\_show\_selection() |
| **phones \[\] word left** | n \= ordinals or 1 user.words\_left(n \- 1\) edit.extend\_word\_left() user.homophones\_show\_selection() |
| **phones \[\] word right** | n \= ordinals or 1 user.words\_right(n \- 1\) edit.extend\_word\_right() user.homophones\_show\_selection() |

# homophones open

| Command | Result |
| :---- | :---- |
| **choose** | result \= user.homophones\_select(number\_small) insert(result) user.homophones\_hide() |
| **choose** | result \= user.homophones\_select(number\_small) insert(user.formatted\_text(result, formatters)) user.homophones\_hide() |

# line commands

| Command | Result |
| :---- | :---- |
| **lend** | edit.line\_end() |
| **bend** | edit.line\_start() |
| **go** | edit.jump\_line(number) |
| **go end** | edit.jump\_line(number) edit.line\_end() |
| **comment \[line\]** | user.select\_range(number, number) code.toggle\_comment() |
| **comment until** | user.select\_range(number\_1, number\_2) code.toggle\_comment() |
| **clear \[line\]** | edit.jump\_line(number) user.select\_range(number, number) edit.delete() |
| **clear until** | user.select\_range(number\_1, number\_2) edit.delete() |
| **copy \[line\]** | user.select\_range(number, number) edit.copy() |
| **copy until** | user.select\_range(number\_1, number\_2) edit.copy() |
| **cut \[line\]** | user.select\_range(number, number) edit.cut() |
| **cut \[line\] until** | user.select\_range(number\_1, number\_2) edit.cut() |
| **(paste | replace) until** | user.select\_range(number\_1, number\_2) edit.paste() |
| **(select | cell | sell) \[line\]** | user.select\_range(number, number) |
| **(select | cell | sell) until** | user.select\_range(number\_1, number\_2) |
| **tab that** | edit.indent\_more() |
| **tab \[line\]** | edit.jump\_line(number) edit.indent\_more() |
| **tab until** | user.select\_range(number\_1, number\_2) edit.indent\_more() |
| **retab that** | edit.indent\_less() |
| **retab \[line\]** | user.select\_range(number, number) edit.indent\_less() |
| **retab until** | user.select\_range(number\_1, number\_2) edit.indent\_less() |
| **drag \[line\] down** | edit.line\_swap\_down() |
| **drag \[line\] up** | edit.line\_swap\_up() |
| **drag up \[line\]** | user.select\_range(number, number) edit.line\_swap\_up() |
| **drag up until** | user.select\_range(number\_1, number\_2) edit.line\_swap\_up() |
| **drag down \[line\]** | user.select\_range(number, number) edit.line\_swap\_down() |
| **drag down until** | user.select\_range(number\_1, number\_2) edit.line\_swap\_down() |
| **clone (line|that)** | edit.line\_clone() |

# numbers

| Command | Result |
| :---- | :---- |
|  | "{number\_string}" |

# symbols

| Command | Result |
| :---- | :---- |
| **question \[mark\]** | "?" |
| **(downscore | underscore)** | "\_" |
| **double dash** | "--" |
| **(bracket | brack | left bracket)** | "{" |
| **(rbrack | are bracket | right bracket)** | "}" |
| **triple quote** | "'''" |
| **(triple grave | triple back tick | gravy)** | insert("\`\`\`") |
| **(dot dot | dotdot)** | ".." |
| **ellipses** | "..." |
| **(comma and | spamma)** | ", " |
| **plus** | "+" |
| **arrow** | "-\>" |
| **dub arrow** | "=\>" |
| **new line** | "\\\\n" |
| **carriage return** | "\\\\r" |
| **line feed** | "\\\\r\\\\n" |
| **empty dubstring** | ""' key(left) |
| **empty escaped (dubstring|dub quotes)** | \\\\"\\\\"' key(left) key(left) |
| **empty string** | "''" key(left) |
| **empty escaped string** | "\\\\'\\\\'" key(left) key(left) |
| **(inside parens | args)** | insert("()") key(left) |
| **inside (squares | square brackets | list)** | insert("\[\]") key(left) |
| **inside (bracket | braces)** | insert("{}") key(left) |
| **inside percent** | insert("%%") key(left) |
| **inside (quotes | string)** | insert("''") key(left) |
| **inside (double quotes | dubquotes)** | insert('""') key(left) |
| **inside (graves | back ticks)** | insert("\`\`") key(left) |
| **angle that** | text \= edit.selected\_text() user.paste("\<{text}\>") |
| **(square | square bracket) that** | text \= edit.selected\_text() user.paste("\[{text}\]") |
| **(bracket | brace) that** | text \= edit.selected\_text() user.paste("{{{text}}}") |
| **(parens | args) that** | text \= edit.selected\_text() user.paste("({text})") |
| **percent that** | text \= edit.selected\_text() user.paste("%{text}%") |
| **quote that** | text \= edit.selected\_text() user.paste("'{text}'") |
| **(double quote | dubquote) that** | text \= edit.selected\_text() user.paste('"{text}"') |
| **(grave | back tick) that** | text \= edit.selected\_text() user.paste('\`{text}\`') |

