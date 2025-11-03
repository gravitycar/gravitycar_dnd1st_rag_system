More and better pre-processing. 

1) Parsing the table of contents (TOC) and the listing of tables (LOT)
Look for the section 


2) Correcting known bad patterns.
The Watermark:
pattern /\n\nMichael Andersen \(.*\)\n\n/
replace: " "

The Crowded Title
pattern /\s## /
replace: \n## 


Opponent Armor class
pattern:
(Opponent Armor) .*\n[\|\-]*\n[\|\s]*(Class)
replace
Group 1 = "Opponent Armor Class" 
group 2 = ''


Assassin table
pattern:
(Level of the) .*\n[\|\-]*\n[\|\s]*(Assassin)
Replace
group 1 = "Level of the Assassin", 
group 2 = ''


Undead Turning
pattern:
(Type of) .*\n[\|\-]*\n[\|\s]*(Undead)
group 1 = "Type of Undead" 
group 2 = ''


Psionic Saving Throws
Pattern:
(Attacked Creature's).*(Throw at Attack Range Medium).*(Saving).*(\|\s*\|)\n[\|\-]*\n.*(Total Intelligence & Wisdom\*\*).*(Short).*(\|\s*\|).*(Long)
Replace:
Group 1 = Attacked Creature's Total Intelligence & Wisdom**
Group 2 = Saving Throw at Attack Range Short
Group 3 = Saving Throw at Attack Range Medium
Group 4 = Saving Throw at Attack Range Long
Group 5 = ''
Group 6 = ''
Group 7 = ''
Group 8 = ''
