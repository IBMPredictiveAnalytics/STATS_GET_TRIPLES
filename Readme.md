# STATS GET TRIPLES
## Read a file in Triple-S format
 Triple-S is an open standard for data files, primarily surveys.  This command reads a fixed-format or csv file conforming to this standard.  It can also generate and save a syntax file for reading the data.

---
Requirements
----
- IBM SPSS Statistics 18 or later and the corresponding IBM SPSS Statistics-Integration Plug-in for Python.

---
Installation intructions
----
1. Open IBM SPSS Statistics
2. Navigate to Utilities -> Extension Bundles -> Download and Install Extension Bundles
3. Search for the name of the extension and click Ok. Your extension will be available.

----
Tutorial
----

Read a file in Triple-S format version 2.0.

STATS GET TRIPLES   
METADATA ="*file*"^&#42;  
DATA = "*file*"  
SYNTAX = "*syntax file*"  
DATAENCODING = LOCALE^&#42;&#42; or UTF8  
EXECUTE = YES or NO^&#42;&#42;  
STRMVCODE = "*string missing value code*"  
MAXDATALENGTH = *number*  

/OPTIONS 
MDVALLABELS = "*label for 0*" "*label for 1*"  
FULLLABELATTR= YES^&#42;&#42; or NO  
REMOVEHTML=YES or NO^&#42;&#42;  
SCORERECODE=YES or NO^&#42;&#42;

/HELP

^&#42; Required  
^&#42;&#42; Default

/HELP displays this help and does nothing else.

Example:
```
STATS GET TRIPLES METADATA="c:/data/mysurvey.xml"
    SYNTAX = "c:/data/mysurvey.sps".
```

The output may be an open dataset, a syntax file that reads
the file, or both.

Triple-S format requires two files.  **METADATA** specifies the
xml metadata data that defines the formatting and any multiple
response information.  HIERARCHY files are not supported.

**DATA** specifies the data file described by the format.  By
default, the data file is assumed to have the same name and
location as the metadata file and extension *txt*.

**DATAENCODING** specifies that the character data are encoded as UTF8 or LOCALE.
The Triple-S standard expects code page 1252 or equivalent, but other
encodings might be encountered in the wild.  LOCALE specifies the
current Statistics LOCALE setting.  The metadata file
is expected to be in utf8.

If the record length is greater than 50000, use
**MAXRECORDLENGTH** = number.  Otherwise, bytes beyond that value
are lost.  It does not matter if the stated length is greater
than the actual.

**SYNTAX** optionally specifies the name of a syntax file that will
contain the syntax to read the data file.

**EXECUTE** specifies whether the syntax (saved or not) should
be executed.  Note that by default the generated syntax is
not executed.

At least one of SYNTAX and EXECUTE=YES must be specified.

OPTIONS
-------
**STRMVCODE** optionally specifies the code to be used for
string variable missing values.  The default action is
to examine the highest value code for a string variable
and increment the last character by one character.

Multiple dichotomy sets are defined with variable values of
0 and 1.  The value labels default to "No" and "Yes".  A pair
of alternative labels can be specified with **MDVALLABELS**.

If variable label text exceeds the SPSS variable label length
limit, which is 255 bytes in current versions, the  text is
truncated.  Specify **FULLLABELATTR**=YES to create a custom
attribute with the full text.

The Triple-S standard does not support HTML markup, but in
practice it may be present.  Specify **REMOVEHTML**=YES to remove
HTML markup from text.  That causes text of the form
`<...>` to be removed, but this could match text that is not
actually an html tag to be deleted.

**SCORERECODE**=YES causes the input values for variables that include
a score attribute in the Value elements to be recoded to the
score values, and the value labels will refer to those values.
Multiple response variables are not recoded.
The scores must be consistent with the variable type: a numeric
variable cannot have string score values.


This command assumes that the xml file conforms to the
Triple-S 2.0 specification.  If it does not, the command
may fail rudely.  Information about the standard can be found at
http://http://www.triple-s.org/.

NOTE: If the Triple-S website is down or the computer does not have internet access, and your sss file
includes the DTD reference, this command will fail.  However,
removing the DTD reference will let it work.  The DTD reference
looks like this.
`<!DOCTYPE sss PUBLIC "-//triple-s//DTD Survey Interchange v1.1//EN" "http://www.triple-s.org/dtd/sss_v11.dtd">`

If multiple response sets are present (multiple dichotomy or
multiple category) the component variable names are generated
from the corresponding input of type "multiple" by appending
an underscore and numerical suffix.  In the unlikely case where
this would cause a name collision, paste and edit the syntax as needed.

For single variables and multiple category sets, if the values element
includes any scores, a custom attribute array named score is created.
Each array element has the form *value|score*, and if value includes
the vertical bar, it is escaped as `\|`.

Notes
-----
Variables of type Date or Time are read as strings.  You can use 
the Date/Time Wizard to convert these to SPSS dates if needed.

No attempt is made to shorten names or labels that exceed the 
maximum lengths supported in Statistics.  

Triple-S names are case sensitive while Statistics names are 
not, so it is possible to have a name collision.

The Triple-S standard requires the comma  as the field separator
in csv format.  If you are reading a csv file and are in a locale
where comma is the decimal character, you may have to change your
Statistics locale in order to read the file.

Language tagged strings are not currently supported.

---
License
----

- Apache 2.0
                              
Contributors
----

  - JKP, IBM SPSS
