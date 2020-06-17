#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989,2020
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/


import random, os, tempfile, textwrap, codecs, re, locale, sys, os.path, time, re
from xml.sax.handler import ContentHandler
import xml.sax
import spss, spssaux
from spssaux import _smartquote as sq
from extension import Template, Syntax, processcmd

"""STATS GET TRIPLES extension command"""

__author__ =  'IBM SPSS, JKP'
__version__=  '1.1.1'

# history
# 31-jan-2014 Original version
# 26-mar-2014 Add option for automatic score recode

helptext = """STATS GET TRIPLES METADATA="filespec DATA="filespec"
SYNTAX = "syntaxfilespec" FILE=LOCALE or UTF8
EXECUTE=YES or NO
STRMVCODE = "string missing value code"
MAXDATALENGTH = number
/OPTIONS MDVALLABELS = 'label for 0' 'label for 1'
FULLLABELATTR= YES or NO REMOVEHTML=YES or NO SCORERECODE=YES or NO
/HELP

METADATA is the only required keyword.

Example:
STATS GET TRIPLES METADATA="c:/data/mysurvey.xml"
    SYNTAX = "c:/data/mysurvey.sps".

This command reads a file in Triple-S format version 2.0.
The output may be an open dataset, a syntax file that reads
the file, or both.

Triple-S format requires two files.  METADATA specifies the
xml metadata data that defines the formatting and any multiple
response information.  HIERARCHY files are not supported.

DATA specifies the data file described by the format.  By
default, the data file is assumed to have the same name and
location as the metadata file and extension "txt".

DATAENCODING specifies that the data are encoded in UTF8 or LOCALE.
The Triple-S standard expects cp 1252 or equivalent, but other
encodings might be encountered in the wild.  The metadata file
is expected to be in utf8.

If the record length is greater than 50000, use
MAXRECORDLENGTH = number.  Otherwise, bytes beyond that value
are lost.  It does not matter if the stated length is greater
than the actual.

SYNTAX optionally specifies the name of a syntax file that will
contain the syntax to read the data file.

EXECUTE specifies whether the syntax (saved or not) should
be executed.

At least one of SYNTAX and EXECUTE=YES must be specified.

STRMVCODE optionally specifies the code to be used for
string variable missing values.  The default action is
to examine the highest value code for a string variable
and increment the last character by one character.

Multiple dichotomy sets are defined with variable values of
0 and 1.  The value labels default to "No" and "Yes".  A pair
of alternative labels can be specified with MDVALLABELS.

If variable label text exceeds the SPSS variable label length
limit, which is 255 bytes in current versions, the  text is
truncated.  Specify FULLLABELATTR=YES to create a custom
attribute with the full text.

The Triple-S standard does not support HTML markup, but in
practice it may be present.  Specify REMOVEHTML=YES to remove
HTML markup from text.  That causes text of the form
<...> to be removed, but this could match text that is not
actually an html tag to be deleted.

SCORERECODE=YES causes the input values for variables that include
a score attribute in the Value elements to be recoded to the
score values, and the value labels will refer to those values.
Multiple response variables are not recoded.
The scores must be consistent with the variable type: a numeric
variable cannot have string score values.

/HELP displays this help and does nothing else.

This command assumes that the xml file conforms to the
Triple-S 2.0 specification.  If it does not, the command
may fail rudely.  Information about the standard can be found at
http://http://www.triple-s.org/.
NOTE: If the Triple-S website is down, and your sss file
includes the DTD reference, this command will fail.  However,
removing the DTD reference will let it work.  The DTD reference
looks like this.
<!DOCTYPE sss PUBLIC "-//triple-s//DTD Survey Interchange v1.1//EN" "http://www.triple-s.org/dtd/sss_v11.dtd">

If multiple response sets are present (multiple dichotomy or
multiple category) the component variable names are generated
from the corresponding input of type "multiple" by appending
an underscore and numerical suffix.  In the unlikely case where
this would cause a name collision, paste and edit the syntax as needed.

For single variables and multiple category sets, if the values element
includes any scores, a custom attribute array named score is created.
Each array element has the form "value|score", and if value includes
the vertical bar, it is escaped as \|.

Notes:
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
"""

def dotriples(metadatafile, syntax=None, data=None, language=None, 
        execute=False, dataencoding="locale", strmvcode = "", maxdatalength=50000,
        removehtml=False, fulllabelattr=True, mdvallabels=["No", "Yes"], scorerecode=False):
    """Execute STATS GET TRIPLES"""
    
# debugging
    ## makes debug apply only to the current thread
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(1)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ###    ###SpssClient._heartBeat(False)
    #except:
        #pass

    if syntax is None and not execute:
        raise ValueError(_("""Neither a syntax file output nor execution was specified: there is nothing to do."""))
    fh = FileHandles()
    metadatafile = fh.resolve(metadatafile)
    if not syntax is None:
        syntax = fh.resolve(syntax)
    if data is not None:
        data = fh.resolve(data)       
    strmvcode = sq(strmvcode)  # default string missing code if values not supplied
    if len(mdvallabels) != 2:
        raise ValueError(_("""Exactly two labels must be supplied for multiple dichotomy set values"""))
    mdsetvallabels = {0 : sq(mdvallabels[0]), 1: sq(mdvallabels[1])}
    
    # handler will hold the parsed information
    handler = metadataHandler(removehtml=removehtml)

    # Retrieve and parse the metadata
    xml.sax.parse(metadatafile, handler)
    
    # Generate syntax
    cmds = gensyntax(handler, metadatafile, data, syntax, strmvcode, 
        dataencoding, maxdatalength, fulllabelattr, mdsetvallabels, scorerecode)
    if not syntax is None:
        writesyntax(cmds, syntax)
        print(_("""Syntax file created: %s""") % syntax)
    if execute:
        try:
            spss.Submit(cmds)
        except UnicodeEncodeError:
            raise ValueError(_("""The metadata contains text invalid in the current character set.
The dataset cannot be created.  Running Statistics in Unicode mode might resolve this problem."""))


class metadataHandler(ContentHandler):
    
    # regular expression for br elements
    brRegex = re.compile(r"<br/*>",flags=re.I)
    htmlelt = re.compile(r"<.+?>")
    def __init__(self, removehtml):
        """Content Handler for Triple-S metadata"""
        
        self.removehtml = removehtml
        # variable definitions
        self.variables = []
        self.state = 'start'
        self.contentstack = []
        self.intext = False
        self.textstack = []

    # callbacks from parser    
    def startElement(self, name, attr):
        if name == 'sss':
            self.datafile = Datafile(getValue(attr, 'version'), getValue(attr, 'languages'),
                getValue(attr, 'modes'))
        elif name == 'survey':
            self.state = 'survey'
        elif name == 'record':
            self.state = 'record'
            self.record = Record(getValue(attr, 'ident'), getValue(attr, 'format'),
                getValue(attr, 'skip'), getValue(attr, 'href'))
            if self.record.format is None:
                self.record.format = "fixed"  #3/26/14
        elif name == 'variable':
            self.variables.append(Variable(**dict(list(zip(['ident','type','use','format'], 
                [getValue(attr, item) for item in ['ident','type','use','format']])))))
        elif name == 'position':
            self.variables[-1].position = [getValue(attr, 'start'),
                getValue(attr, 'finish')]
        elif name == "spread":
            self.variables[-1].spreadsubfields = getValue(attr, 'subfields')
            self.variables[-1].spreadwidth = getValue(attr, 'width')
        elif name == 'range':
            self.variables[-1].rangefrom = getValue(attr, 'from')
            self.variables[-1].rangeto = getValue(attr, 'to')
        elif name == 'value':
            self.code = getValue(attr, 'code')
            ###self.variables[-1]. = self.code
            self.variables[-1].scores[self.code] = getValue(attr, 'score')
        elif name == "text":
            self.variables[-1].mode = getValue(attr, "mode")
            self.intext = True
        elif name == 'hierarchy':
            raise ValueError(_("""Hierarchy files are not supported by this procedure"""))
            
    def endElement(self, name):
        if name == "br":
            if self.intext:
                self.textstack.append(" - ")
            else:
                self.contentstack.append(" - ")
        elif self.state in ['start', 'survey'] and name in ['date', 'time', 'origin', 'user', 'name', 'version', 'title']:
            self.addContent(self.datafile, name)
        elif self.state in ['record'] and name in ['name', 'label']:
            self.addContent(self.variables[-1], name)
        elif name == "filter":   # missing value
            self.variables[-1].filter = self.contentstack[0]
            self.contentstack = []
        elif name == 'value':
            self.variables[-1].values[self.code] = self.clean(self.contentstack)
            self.contentstack = []
        elif name == "size":
            self.variables[-1].size = self.contentstack[0]
            self.contentstack = []
        elif name == "text":
            if self.variables[-1].mode:
                ###self.variables[-1].text.append("Mode: %s.  %s" % (self.variables[-1].mode, "\n".join(self.textstack)))
                self.variables[-1].text.append("Mode: %s.  %s" % (self.variables[-1].mode, self.clean(self.textstack)))
                mode = ""
            else:
                self.variables[-1].text.append("\n".join(self.textstack)        )
            self.intext = False
            self.textstack = []
            
        if name == 'sss':
            return   'all done'
            
    def characters(self, content):
            """Callback for text content in element"""
            
            if content.rstrip() != "":
                if self.intext:
                    self.textstack.append(content)
                else:
                    self.contentstack.append(content)

    def addContent(self, item, name):
        """Add or create named content to item
        
        item is the object to receive the content
        name is the attribute name"""
        
        if self.intext:
            if self.textstack:
                #text = re.sub(metadataHandler.brRegex, r" - ", "".join(self.textstack))
                #if self.removehtml:
                    #text = re.sub(metadataHandler.htmlelt, "", text)                
                #setattr(item,name, "\n".join(self.text))
                setattr(item, name, self.clean(self.text))
                self.textstack = []
        else:
            if self.contentstack:
                #text = re.sub(metadataHandler.brRegex, r" - ", "".join(self.contentstack))
                #if self.removehtml:
                    #text = re.sub(metadataHandler.htmlelt, "", text)
                setattr(item, name, self.clean(self.contentstack))
                self.contentstack = []            
    def clean(self, stack):
        """Clean out html if option specified and return line
        
        stack is the list of lines to process"""
        
        text = re.sub(metadataHandler.brRegex, r" - ", "".join(stack))
        if self.removehtml:
            text = re.sub(metadataHandler.htmlelt, "", text)
        return text
        
def getValue(attr, name):
    """Return attribute value or None"""
    
    try:
        return attr.getValue(name)
    except:
        return None

class Variable(object):
    formatdict = {
        "single" : "F",   # numeric: integers, strings any. Width determined by mandatory value element
        "multiple" : "F",      # mandatory values; optional spread
        "quantity" : "F",      # mandatory values
        "character" : "A",     # mandatory size element
        "logical" : "F",       # one column 0/1
        "date" : "A",      # YYYYMMDD
        "time" : "A"}       # always six characters HHMMSS
    
    def __init__(self, ident, type, use="regular", format="numeric"):
        attributesFromDict(locals())
        # types are
        #single Mandatory values element
        #multiple Optional spread element
        #Mandatory values element
        #quantity Mandatory values element
        #character Mandatory size element
        #logical Nothing extra
        #date Optional values element
        #time Optional values element        
        #fixed format: starting and ending columns, 1 based
        #csv format: field number, 1 based
        self.position = [None, None]
        self.values={}
        self.label = None
        self.filter = None
        self.scores = {}
        self.spreadsubfields = None
        self.spreadwidth = None
        self.size = None
        self.rangefrom = None
        self.rangeto = None
        self.text = []
        self.vardeflist = []
        
        #special use types can be serial or weight
        
    def getWeight(self):
        """Return weight syntax or empty list"""
        
        if self.use == "weight":
            return ["WEIGHT BY %s." % self.name]
        else:
            return []

    def getDataList(self, recordformat):
        """Return data list or get data variable definition syntax for one variable or MR set"""
        
        format = Variable.formatdict[self.type]
        if self.format == "literal":
            format = "A"
        if self.type == "date" and recordformat == "csv":
            format = "A8"
        elif self.type == "time" and recordformat == "csv":
            format = "A6"
        if self.type != "multiple":
            self.vardef = self.name
            varcount = 1
            self.multtype = None
        else:
            if self.spreadwidth is not None:
                width = int(self.spreadwidth)
            else:
                width = 1
            if self.spreadsubfields is not None:  # MC set
                varcount = self.spreadsubfields
                self.multtype = "MC"
            else: #MD set (bitstring format)
                self.multtype = "MD"
                if self.position[1] is None:
                    endloc = max((int(k) for k in list(self.values.keys()))) + int(self.position[0]) - 1
                else:
                    endloc = int(self.position[1])
                varcount = (endloc - int(self.position[0]) + 1) // width
            self.vardef = self.name + "_1 TO " + self.name + "_" + str(varcount)
            self.vardeflist = [self.name + "_" + str(i+1) for i in range(int(varcount))]

            if recordformat == "fixed":
                return "%s (%sF%d)" % (self.vardef, varcount, width)
            else:  # csv, and md values are not comma separated!
                if self.multtype == "MD":
                    self.mdwidth = width
                    return [int(self.position[0]), "%s A" % self.name]
                else:
                    vlist = ["%s %s" % (name, format) for name in self.vardeflist]
                    ###return [int(self.position[0]), " ".join(vlist)]
                    self.mdwidth = width  # required field if csv
                    return [int(self.position[0]), "%s A" %self.name]  # just the main variable name for now
        if recordformat == "fixed":
            if self.position[1] is not None:
                width = int(self.position[1]) - int(self.position[0]) + 1
            # second position element can be omitted if width is 1
            else:
                width = 1            
            return "%s %s-%d (%s)" % (self.vardef, self.position[0], int(self.position[0]) + width - 1, format)
        else: 
            # return csv specs as a duple of position (order) and spec repeated
            # for each variable if multiple
            
            if self.type != "multiple":
                return [int(self.position[0]), "%s %s" % (self.vardef, format)]
            else:
                # position indicates field order in csv format
                vlist = ["%s %s" % (name, format) for name in self.vardeflist]
                return [int(self.position[0]), " ".join(vlist)]
            
    def fixupCsv(self, recordformat):
        """Create set member variables for MR sets from a single string variable
        
        recordformat is csv or fixed"""
        
        if recordformat == "fixed" or self.multtype is None:
            return []
        cmds = []
        position = 1
        ###if self.multtype == "MD":
        # break each MD set variable out of one common string variable in width increments
        for vnum in range(len(self.vardeflist)):
            vnum1 = vnum + 1
            vname = self.name + "_" + str(vnum1)
            # We use the char version here, but strings will be all numeric
            #cmds.append("""COMPUTE %s = NUMBER(CHAR.SUBSTR(%s, %s, %s), F%s.0).""" %\
                #(vname, self.name, position, self.mdwidth, self.mdwidth))            
            cmds.append("""IF (CHAR.LENGTH(CHAR.SUBSTR(%s, %s, %s)) > 0) %s = NUMBER(CHAR.SUBSTR(%s, %s, %s), F%s.0).""" %\
                (self.name, position, self.mdwidth, vname, self.name, position, self.mdwidth, self.mdwidth))
            position += self.mdwidth
        return cmds
    
    @staticmethod
    def calcwidthfixed(position, format, size, values, spread):
        """Return width of the variable for fixed width format"""
        
        if position[1] is not None:
            return int(position[1]) - int(position[0]) + 1
        # second position element can be omitted if width is 1
        else:
            return 1
        
    def getVarLabel(self, val, fulllabelattr, tw):
        """Return variable label syntax or empty list and value labels for MD sets
        
        val is the value label dictionary
        tw is a text wrapper object"""
        
        if self.vardeflist:  # mult response
            if self.spreadsubfields: #MC set
                if self.label:
                    cmds = []
                    for name in self.vardeflist:
                        cmds.append("VARIABLE LABELS %s %s." % (name, sq(self.label)))
                        cmds.extend(self.getFullLabelAttr(name, self.label, fulllabelattr, tw))
                    return cmds
                else:
                    return []
            else: # MD set.  return value labels where available
                cmds = []
                self.mdsetvars = []
                for vnum in range(len(self.vardeflist)):
                    vnum1 = vnum + 1
                    vname = self.name + "_" + str(vnum1)
                    if str(vnum1) in self.values:
                        self.mdsetvars.append(vname)  # building list of names for set definition
                        ###cmds.append("VARIABLE LABELS %s %s." % (vname, sq(" ".join(self.values[str(vnum1)]))))
                        cmds.append("VARIABLE LABELS %s %s." % (vname, sq("".join(self.values[str(vnum1)]))))
                        cmds.extend(self.getFullLabelAttr(vname, "".join(self.values[str(vnum1)]),
                            fulllabelattr, tw))
                wrapped = "\n".join(tw.wrap(" ".join(self.vardeflist)))
                cmds.append("""VALUE LABELS %s
0 %s 1 %s.""" % (wrapped, val[0], val[1]))
                return cmds
        else:
            if self.label is not None:
                cmds = ["VARIABLE LABELS %s %s." % (self.name, sq(self.label))]
                cmds.extend(self.getFullLabelAttr(self.name, self.label, fulllabelattr, tw))
                return cmds
            else:
                return []
    
    def getValueLabels(self, scorerecode):
        """Return value label syntax or empty list
        
        scorerecode indicates whether labels are for values or scores.
        It is ignored if there are no scores"""
        
        if self.vardeflist and self.spreadsubfields is None:  #MD sets get labels elsewhere
            return []
        
        if not any(self.scores.values()):
            scorerecode = False
        isstring = self.format == "literal"  # (default is numeric)
        if not self.values:
            return []
        else:
            result = ["VALUE LABELS %s" % self.vardef]
            try:
                for k,v in sorted(self.values.items()):
                    if scorerecode:
                        k = self.scores[k]
                    kk = k
                    if isstring:
                        k = sq(k)
                    result.append(" ".join([k, sq(v)]))
            except:
                raise ValueError(_("""Variable %s has a value, %s for which there is no score""")\
                    % (self.vardef, k))
            result[-1] = result[-1] + "."
            return result
        
    def getScores(self):
        """Return custom attribute "score" """
        
        # Score attribute will be an array with each element having the form
        # value|score
        # In the unlike event that the value contains "|" it is escaped as "\|"
        
        if (self.vardeflist and self.spreadsubfields is None)\
           or not any(self.scores.values()):
            return []
        else:
            namelist = "\n".join(self.vardeflist) or self.name
            result = ["VARIABLE ATTRIBUTE VARIABLES = %s ATTRIBUTE=" % namelist]
            itemnum = 1
            for k, v in sorted(self.scores.items()):
                if v is not None:
                    result.append("""score[%s](%s)""" % (itemnum, sq(k.replace("|", "\|") + " | " + v)))
                    itemnum += 1
            result[-1] = result[-1] + "."
            return result
            
    def getRecode(self):
        """Return recode for variable into itself or empty"""
        
        if not any(self.scores.values()):
            return []
        result = ["RECODE  %s" % self.vardef]
        isstring = self.format == "literal"  # (default is numeric)
        for k,v in sorted(self.scores.items()):
            kk = k
            if v is not None:
                if isstring:
                    k = sq(k)
                    v = sq(v)
                result.append("(%s=%s)" % (k, v))
        result[-1] = result[-1] + "."
        return result
        
        
    def getMissing(self, strmvcode):
        """Return missing value computation and syntax"""
        
        if self.filter is None:
            return []                # no missing values defined
        self.mvcode = self.makemvcode(strmvcode)   # will be quoted if string type
        return ["""IF (NOT %(filter)s) %(name)s = %(mvcode)s.
MISSING VALUES %(name)s (%(mvcode)s).""" % self.__dict__]
    
    def getText(self):
        """Return custom attribute array syntax as a list"""
        
        if not self.text:
            return []
        attrdef = ["Text[%s](%s)" % (i+1, sq(item)) for i, item in enumerate(self.text)]
        return ["VARIABLE ATTRIBUTE VARIABLES=%s ATTRIBUTE=%s." % (self.name, "\n".join(attrdef))]

    def getMRset(self):
        """Return MD or MR set syntax"""
        
        if self.type != "multiple":
            return []
        if self.spreadsubfields:
        # spread format = MC group
            cmd = """MRSETS /MCGROUP NAME=$%s LABEL=%s 
VARIABLES=%s.""" % (self.name, 
                sq(self.label), self.vardef)
        else:  #MD group
            cmd = """MRSETS /MDGROUP name=$%s LABEL=%s 
VARIABLES=%s 
VALUE=1.""" % (self.name, 
                sq(self.label), " ".join(self.mdsetvars))
        return [cmd]
        
    def getFullLabelAttr(self, varname, label, fulllabelattr, tw):
        """Return custom attribute syntax as a list for label if fulllabelattr or empty list
        
        varname is the variable
        label is the variable label
        fulllabelattr is True or False on whether to create the attribute
        tw is a text wrapper"""
        
        if not fulllabelattr:
            return []
        
        wrapped = tw.wrap(label)
        lines = [sq(item + " ") for item in wrapped]
        lastline = len(lines) - 1
        
        cmd = ["VARIABLE ATTRIBUTE VARIABLES = %s ATTRIBUTE = FullLabelText(" % varname]
        for linenumber, line in enumerate(lines):
            if linenumber < lastline:
                cmd.append(line + "+")
            else:
                cmd.append(line + ").")
        return cmd
        
    def makemvcode(self, strmvcode):
        """Return a possibly quoted code to use for representing missing values"""
        
        if not self.values:
            if self.format == "literal":
                return strmvcode
            else:
                return "$SYSMIS"   # would not work for strings
        if self.rangeto is not None:   # not allowed for literals
            return str(float(self.rangeto) * 100 + 1)  # add 1 in case rangeto is 0
        else:
            biggest = max(self.values.keys())
            if self.format != "literal":
                return biggest * 10 + 1   # add 1 in case biggest is 0
            else:
                # use the next character code after the code of the last character
                # and hope that it is defined as an actual character
                biggest = biggest[:-1] + chr(ord(biggest[-1])+1)
                return sq(biggest)
        
class Datafile(object):
    def __init__(self, version, languages, mode):
        attributesFromDict(locals())
        
    def get(self):
        "Return ADD DOCUMENT syntax for attributes"
        
        # Selected attributes are generated first followed by any other
        # attributes in alpha order
        
        doc = ['ADD DOCUMENT ']
        priority = ['title', 'name','version', 'date']
        for item in priority:
            if hasattr(self, item):
                doc.extend(quoteprefixandlist(item + ": ", getattr(self,item)))
        for k, v in sorted(self.__dict__.items()):
            if k not in priority and v is not None :
                doc.extend(quoteprefixandlist(k + ": ", v))
        doc[-1] = doc[-1] + "."
        return doc
        
def quoteprefixandlist(prefix, items):
    """Return list with prefix and first item on one line plus others all smartquoted
    
    prefix is the prefix for the first line - can be None
    items is a string or list of items that may contain newlines"""
    
    if not spssaux._isseq(items):
        items = [items]
    # Make each line a separate list member
    items = [jitem for jitem in flatten([item.split("\n") for item in items])]
    if prefix is not None:
        result = [prefix + items[0]]
        result.extend(items[1:])
    else:
        result = items
    return [sq(item) for item in result]

def flatten(seq):
    "generator for a flattened version of seq, which must be a sequence"
    
    for item in seq:
        if spssaux._isseq(item):
            for subitem in flatten(item):
                yield subitem
        else:
            yield item
            
class Record(object):
    def __init__(self, ident, format, skip, href):
        attributesFromDict(locals())

def gensyntax(par, metadatafile, data, syntax, strmvcode, dataencoding, 
        maxdatalength, fulllabelattr, mdsetvallabels, scorerecode):
    """Return syntax as list of lines
    
    par is a metadata handler object
    metadatafile is the name of the xml file with the definitions
    data is the name of the data file
    If data is None, the name is derived from the metadatafile name
    syntax is the filename to write to or None
    strmvcode is the code to be used for missing data in strings
    dataencoding is the encoding to be assumed for the data
    maxdatalength is >= the maximum record length
    fulllabelattr is flag for whether to generate full label attribute
    mdsetvallabels is a two-element dictionary for MD set value labels"""
    
    spssver = spss.GetDefaultPlugInVersion()
    encodingkwdok = int(spssver[4:]) >= 210
    tw = textwrap.TextWrapper(width=100, break_long_words=False, break_on_hyphens=False)
    if data is None:
        data = os.path.splitext(metadatafile)[0] + "." + "txt"    
    cmds = []
    cmds.append(["""* Syntax created by STATS GET TRIPLES on %s.""" % time.asctime()])
    cmds.append(["""* Metadata file: %s.""" % metadatafile])

    handle = "D" + str(random.uniform(.1, 1))
    cmds.append("""FILE HANDLE %s /NAME ="%s" /LRECL=%s.""" % (handle, data, maxdatalength))
   
    if par.record.format == "fixed":
        cmds.append(["""DATA LIST FIXED FILE="%s" ENCODING=%s/""" % (handle, dataencoding)])
        cmds.extend((var.getDataList(par.record.format) for var in par.variables))
    else:
        firstcase = par.record.skip
        if firstcase is None:
            firstcase = 1
        else:
            firstcase = int(firstcase) + 1
        if encodingkwdok:
            enc = "/ENCODING= %s" % dataencoding
        else:
            enc = ""
        cmds.append(["""GET DATA /TYPE = TXT /FILE="%s" %s
    /FIRSTCASE=%s /DELIMITERS="," /QUALIFIER='"'/VARIABLES = """ % (handle, enc, firstcase)])
        items = sorted((var.getDataList(par.record.format) for var in par.variables))
        cmds.extend([item[1] for item in items])
    cmds[-1] = cmds[-1] + "."
    # For MD set variables and csv format, need to break out the component variables
    for var in par.variables:
        cmds.extend(var.fixupCsv(par.record.format))

    # add document - data file must be defined first
    # items are assumed to fit SPSS line length limits from here on
    cmds.extend(par.datafile.get())
    metadata = []
    for var in par.variables:
        metadata.extend(var.getVarLabel(mdsetvallabels, fulllabelattr, tw))
        metadata.extend(var.getValueLabels(scorerecode))
        metadata.extend(var.getScores())
        metadata.extend(var.getMissing(strmvcode))
        metadata.extend(var.getText())
        metadata.extend(var.getMRset())
        metadata.extend(var.getWeight())
        if scorerecode:
            metadata.extend(var.getRecode())
    
    # clear out empty syntax and replace quote escape with SPSS convention
    metadata = [item.replace("&quot;", '""') for item in metadata if item]
    cmds.extend(metadata)
    for i in range(len(cmds)):
        if isinstance(cmds[i], list):
            cmds[i] = cmds[i][0]
        
    return cmds

def writesyntax(syntax, syntaxfile):
    """Write syntax to file in proper encoding
    
    syntax is the list of commands to write
    syntaxfile is the file to write to with file handles resolved"""
    
    unicodemode = spss.PyInvokeSpss.IsUTF8mode()
    if unicodemode:
        ###ec = codecs.getencoder("utf_8")   # must figure string length in bytes of utf-8    
        inputencoding = "unicode_internal"
        outputencoding = "utf_8_sig"
        nl = "\n"
    else:
        inputencoding = locale.getlocale()[1]
        outputencoding = inputencoding
        nl = "\n"
    with codecs.EncodedFile(codecs.open(syntaxfile, "wb"), inputencoding, outputencoding) as f:
        try:
            for line in syntax:
                f.write(line + nl)
        except UnicodeEncodeError:
            raise ValueError(_("""The metadata contains text invalid in the current character set.
The syntax file cannot be written in that character set.
Running Statistics in Unicode mode might resolve this problem."""))

def attributesFromDict(d):
    """build self attributes from a dictionary d."""
    self = d.pop('self')
    for name, value in d.items():
        setattr(self, name, value)

def StartProcedure(procname, omsid):
    """Start a procedure
    
    procname is the name that will appear in the Viewer outline.  It may be translated
    omsid is the OMS procedure identifier and should not be translated.
    
    Statistics versions prior to 19 support only a single term used for both purposes.
    For those versions, the omsid will be use for the procedure name.
    
    While the spss.StartProcedure function accepts the one argument, this function
    requires both."""
    
    try:
        spss.StartProcedure(procname, omsid)
    except TypeError:  #older version
        spss.StartProcedure(omsid)

class FileHandles(object):
    """manage and replace file handles in filespecs.
    
    For versions prior to 18, it will always be as if there are no handles defined as the necessary
    api is new in that version, but path separators will still be rationalized.
    """
    
    def __init__(self):
        """Get currently defined handles"""
        
        # If the api is available, make dictionary with handles in lower case and paths in canonical form, i.e.,
        # with the os-specific separator and no trailing separator
        # path separators are forced to the os setting
        if os.path.sep == "\\":
            ps = r"\\"
        else:
            ps = "/"
        try:
            self.fhdict = dict([(h.lower(), (re.sub(r"[\\/]", ps, spec.rstrip("\\/")), encoding))\
                for h, spec, encoding in spss.GetFileHandles()])
        except:
            self.fhdict = {}  # the api will fail prior to v 18
    
    def resolve(self, filespec):
        """Return filespec with file handle, if any, resolved to a regular filespec
        
        filespec is a file specification that may or may not start with a handle.
        The returned value will have os-specific path separators whether or not it
        contains a handle"""
        
        parts = re.split(r"[\\/]", filespec)
        # try to substitute the first part as if it is a handle
        parts[0] = self.fhdict.get(parts[0].lower(), (parts[0],))[0]
        return os.path.sep.join(parts)
    
    def getdef(self, handle):
        """Return duple of handle definition and encoding or None duple if not a handle
        
        handle is a possible file handle
        The return is (handle definition, encoding) or a None duple if this is not a known handle"""
        
        return self.fhdict.get(handle.lower(), (None, None))
    
    def createHandle(self, handle, spec, encoding=None):
        """Create a file handle and update the handle list accordingly
        
        handle is the name of the handle
        spec is the location specification, i.e., the /NAME value
        encoding optionally specifies the encoding according to the valid values in the FILE HANDLE syntax."""
        
        spec = re.sub(r"[\\/]", re.escape(os.path.sep), spec)   # clean up path separator
        cmd = """FILE HANDLE %(handle)s /NAME="%(spec)s" """ % locals()
        # Note the use of double quotes around the encoding name as there are some encodings that
        # contain a single quote in the name
        if encoding:
            cmd += ' /ENCODING="' + encoding + '"'
        spss.Submit(cmd)
        self.fhdict[handle.lower()] = (spec, encoding)

def Run(args):
    """Execute the STATS TRIPLES extension command"""

    args = args[list(args.keys())[0]]

    oobj = Syntax([
        Template("METADATA", subc="",  ktype="literal", var="metadatafile"),
        Template("DATA", subc="",  ktype="literal", var="data"),
        Template("SYNTAX", subc="",  ktype="literal", var="syntax"),
        Template("LANGUAGE", subc="", ktype="literal", var="language"),
        Template("EXECUTE", subc="", ktype="bool", var='execute'),
        Template("STRMVCODE", subc="", ktype="literal", var="strmvcode"),
        Template("DATAENCODING", subc="", ktype="str", var="dataencoding"),
        Template("MAXDATALENGTH", subc="", ktype="int", var="maxdatalength"),
        
        Template("REMOVEHTML", subc="OPTIONS", ktype="bool", var="removehtml"),
        Template("FULLLABELATTR", subc="OPTIONS", ktype="bool", var="fulllabelattr"),
        Template("MDVALLABELS", subc="OPTIONS", ktype="literal", var="mdvallabels", islist=True),
        Template("SCORERECODE", subc="OPTIONS", ktype="bool", var="scorerecode"),
        
        Template("HELP", subc="", ktype="bool")])
    
    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg
    # A HELP subcommand overrides all else
    if "HELP" in args:
        #print helptext
        helper()
    else:
        processcmd(oobj, args, dotriples)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print(("Help file not found:" + helpspec))
try:    #override
    from extension import helper
except:
    pass