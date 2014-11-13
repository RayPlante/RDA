################################################################################
#
# File Name: ajax.py
# Application: compose
# Purpose:   
#
# Author: Sharief Youssef
#         sharief.youssef@nist.gov
#
#         Guillaume SOUSA AMARAL
#         guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################

import re
from django.utils import simplejson
from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register
from django.conf import settings
from mongoengine import *
from mgi.models import Template, Type, XML2Download
import lxml.etree as etree
from io import BytesIO
import hashlib

# XSL file loading
import os

################################################################################
# 
# Function Name: setCurrentTemplate(request,templateFilename,templateID)
# Inputs:        request - 
#                templateFilename -  
# Outputs:       JSON data with success or failure
# Exceptions:    None
# Description:   Set the current template to input argument.  Template is read 
#                into an xsdDocTree for use later.
#
################################################################################
@dajaxice_register
def setCurrentTemplate(request,templateFilename,templateID):
    print 'BEGIN def setCurrentTemplate(request)'

    request.session['currentComposeTemplate'] = templateFilename
    request.session['currentComposeTemplateID'] = templateID
    request.session.modified = True
    print '>>>>' + templateFilename + ' set as current template in session'
    dajax = Dajax()

    if templateID != "new":
        templateObject = Template.objects.get(pk=templateID)
        xmlDocData = templateObject.content
        request.session['xmlTemplateCompose'] = xmlDocData
        request.session['newXmlTemplateCompose'] = xmlDocData
    else:
        base_template_path = os.path.join(settings.SITE_ROOT, 'static/resources/xsd/new_base_template.xsd')
        base_template_file = open(base_template_path, 'r')
        base_template_content = base_template_file.read()
        request.session['xmlTemplateCompose'] = base_template_content
        request.session['newXmlTemplateCompose'] = base_template_content

    print 'END def setCurrentTemplate(request)'
    return dajax.json()


################################################################################
# 
# Function Name: setCurrentUserTemplate(request,templateID)
# Inputs:        request - 
#                templateFilename -  
# Outputs:       JSON data with success or failure
# Exceptions:    None
# Description:   Set the current template to input argument.  Template is read 
#                into an xsdDocTree for use later.
#
################################################################################
@dajaxice_register
def setCurrentUserTemplate(request,templateID):
    print 'BEGIN def setCurrentUserTemplate(request)'    

    
    request.session['currentComposeTemplateID'] = templateID
    request.session.modified = True
    
    dajax = Dajax()
    
    templateObject = Template.objects.get(pk=templateID)
    request.session['currentComposeTemplate'] = templateObject.title
    xmlDocData = templateObject.content
    request.session['xmlTemplateCompose'] = xmlDocData
    request.session['newXmlTemplateCompose'] = xmlDocData

    print 'END def setCurrentUserTemplate(request)'
    return dajax.json()
################################################################################
# 
# Function Name: verifyTemplateIsSelected(request)
# Inputs:        request - 
# Outputs:       JSON data with templateSelected 
# Exceptions:    None
# Description:   Verifies the current template is selected.
# 
################################################################################
@dajaxice_register
def verifyTemplateIsSelected(request):
    print 'BEGIN def verifyTemplateIsSelected(request)'
    if 'currentComposeTemplate' in request.session:
        print 'template is selected'
        templateSelected = 'yes'
    else:
        print 'template is not selected'
        templateSelected = 'no'
    dajax = Dajax()

    print 'END def verifyTemplateIsSelected(request)'
    return simplejson.dumps({'templateSelected':templateSelected})

################################################################################
# 
# Function Name: isNewTemplate(request)
# Inputs:        request - 
# Outputs:       JSON data with templateSelected 
# Exceptions:    None
# Description:   Verifies the current template is new.
# 
################################################################################
@dajaxice_register
def isNewTemplate(request):    
    if 'currentComposeTemplateID' in request.session and request.session['currentComposeTemplateID'] == "new":
        newTemplate = 'yes'
    else:
        newTemplate = 'no'
    dajax = Dajax()
    
    return simplejson.dumps({'newTemplate':newTemplate})

################################################################################
# 
# Function Name: downloadTemplate(request)
# Inputs:        request - 
# Outputs:       JSON data with templateSelected 
# Exceptions:    None
# Description:   Download the template file
# 
################################################################################
@dajaxice_register
def downloadTemplate(request):
    dajax = Dajax()
    
    xmlString = request.session['newXmlTemplateCompose']
    
    xml2download = XML2Download(xml=xmlString).save()
    xml2downloadID = str(xml2download.id)
    
    dajax.redirect("/compose/download-XSD?id="+xml2downloadID)
    
    return dajax.json()
################################################################################
# 
# Function Name: loadXML(request)
# Inputs:        request - 
# Outputs:       JSON data with templateSelected 
# Exceptions:    None
# Description:   Loads the XML data in the compose page. First transforms the data.
# 
################################################################################
@dajaxice_register
def loadXML(request):
    dajax = Dajax()
    
    # get the original string
    xmlString = request.session['xmlTemplateCompose']
    # reset the string
    request.session['newXmlTemplateCompose'] = xmlString
    
    request.session['includedTypesCompose'] = []
    
    xsltPath = os.path.join(settings.SITE_ROOT, 'static/resources/xsl/xsd2html.xsl')
    xslt = etree.parse(xsltPath)
    transform = etree.XSLT(xslt)
    xmlTree = ""
    if (xmlString != ""):
        request.session['namespacesCompose'] = get_namespaces(BytesIO(str(xmlString)))
        for prefix, url in request.session['namespacesCompose'].items():
            if (url == "{http://www.w3.org/2001/XMLSchema}"):            
                request.session['defaultPrefixCompose'] = prefix
                break
        dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
        newdom = transform(dom)
        xmlTree = str(newdom)
    
    dajax.assign("#XMLHolder", "innerHTML", xmlTree)
    
    return dajax.json()

def get_namespaces(file):
    "Reads and returns the namespaces in the schema tag"
    events = "start", "start-ns"
    ns = {}
    for event, elem in etree.iterparse(file, events):
        if event == "start-ns":
            if elem[0] in ns and ns[elem[0]] != elem[1]:
                raise Exception("Duplicate prefix with different URI found.")
            ns[elem[0]] = "{%s}" % elem[1]
        elif event == "start":
            break
    return ns


################################################################################
# 
# Function Name: insertElementSequence(request, typeID, xpath)
# Inputs:        request - HTTP request
#                typeID - ID of the inserted type
#                xpath - xpath where the element is added
# Outputs:       JSON 
# Exceptions:    None
# Description:   insert the type in the original schema
# 
################################################################################
@dajaxice_register
def insertElementSequence(request, typeID, xpath, typeName):
    dajax = Dajax()
    
    defaultPrefix = request.session['defaultPrefixCompose']
    namespace = request.session['namespacesCompose'][defaultPrefix]
    
    xmlString = request.session['newXmlTemplateCompose']
    dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
    
    # set the element namespace
    xpath = xpath.replace(defaultPrefix +":", namespace)
    # add the element to the sequence
    dom.find(xpath).append(etree.Element(namespace+"element", attrib={'type':typeName, 'name':typeName}))
    
    # add the id of the type if not already present
    if typeID not in request.session['includedTypesCompose']:
        request.session['includedTypesCompose'].append(typeID)
        includedType = Type.objects.get(pk=typeID)
        dom.getroot().insert(0,etree.Element(namespace+"include", attrib={'schemaLocation':includedType.filename}))
    
    # save the tree in the session
    request.session['newXmlTemplateCompose'] = etree.tostring(dom) 
    print etree.tostring(dom)
    
    return dajax.json()

################################################################################
# 
# Function Name: renameElement(request, xpath, newName)
# Inputs:        request - HTTP request
#                xpath - 
#                newName - 
# Outputs:       JSON 
# Exceptions:    None
# Description:   replace the current name of the element by the new name
# 
################################################################################
@dajaxice_register
def renameElement(request, xpath, newName):
    dajax = Dajax()
    
    defaultPrefix = request.session['defaultPrefixCompose']
    namespace = request.session['namespacesCompose'][defaultPrefix]
    
    xmlString = request.session['newXmlTemplateCompose']
    dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
    
    # set the element namespace
    xpath = xpath.replace(defaultPrefix +":", namespace)
    # add the element to the sequence
    dom.find(xpath).attrib['name'] = newName
    
    # save the tree in the session
    request.session['newXmlTemplateCompose'] = etree.tostring(dom) 
    
    return dajax.json()

################################################################################
# 
# Function Name: saveTemplate(request, templateName)
# Inputs:        request - HTTP request
#                templateName - 
# Outputs:       JSON 
# Exceptions:    None
# Description:   save the current template in the database
# 
################################################################################
@dajaxice_register
def saveTemplate(request, templateName):
    dajax = Dajax()
    
    hash = hashlib.sha1(request.session['newXmlTemplateCompose'])
    hex_dig = hash.hexdigest()
    template = Template(title=templateName, filename=templateName, content=request.session['newXmlTemplateCompose'], hash=hex_dig, user=request.user.id)
    template.save()
    print template.id

    return dajax.json()


################################################################################
# 
# Function Name: getOccurrences(request, xpath)
# Inputs:        request - HTTP request
#                xpath -  
# Outputs:       JSON 
# Exceptions:    None
# Description:   Get the occurrences of the selected element
# 
################################################################################
@dajaxice_register
def getOccurrences(request, xpath):
    dajax = Dajax()
    
    defaultPrefix = request.session['defaultPrefixCompose']
    namespace = request.session['namespacesCompose'][defaultPrefix]
    
    xmlString = request.session['newXmlTemplateCompose']
    dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
    
    # set the element namespace
    xpath = xpath.replace(defaultPrefix +":", namespace)
    # add the element to the sequence
    element = dom.find(xpath)
    minOccurs = "1"
    maxOccurs = "1"
    if 'minOccurs' in element.attrib:
        minOccurs = element.attrib['minOccurs']
    if 'maxOccurs' in element.attrib:
        maxOccurs = element.attrib['maxOccurs']
    
    occurs = {'minOccurs':minOccurs, 'maxOccurs':maxOccurs}
    dajax.add_data(occurs, 'getOccurrencesCallback')
    
    return dajax.json()


################################################################################
# 
# Function Name: setOccurrences(request, xpath, minOccurs, maxOccurs)
# Inputs:        request - HTTP request
#                xpath -  
#                minOccurs -
#                maxOccurs - 
# Outputs:       JSON 
# Exceptions:    None
# Description:   Set the occurrences of the selected element
# 
################################################################################
@dajaxice_register
def setOccurrences(request, xpath, minOccurs, maxOccurs):
    dajax = Dajax()
    
    defaultPrefix = request.session['defaultPrefixCompose']
    namespace = request.session['namespacesCompose'][defaultPrefix]
    
    xmlString = request.session['newXmlTemplateCompose']
    dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
    
    # set the element namespace
    xpath = xpath.replace(defaultPrefix +":", namespace)
    # add the element to the sequence
    element = dom.find(xpath)
    element.attrib['minOccurs'] = minOccurs
    element.attrib['maxOccurs'] = maxOccurs
    
    # save the tree in the session
    request.session['newXmlTemplateCompose'] = etree.tostring(dom) 
    
    return dajax.json()


################################################################################
# 
# Function Name: deleteElement(request, xpath)
# Inputs:        request - HTTP request
#                xpath - 
# Outputs:       JSON 
# Exceptions:    None
# Description:   delete the element from the template
# 
################################################################################
@dajaxice_register
def deleteElement(request, xpath):
    dajax = Dajax()
    
    defaultPrefix = request.session['defaultPrefixCompose']
    namespace = request.session['namespacesCompose'][defaultPrefix]
    
    xmlString = request.session['newXmlTemplateCompose']
    dom = etree.parse(BytesIO(xmlString.encode('utf-8')))
    
    # set the element namespace
    xpath = xpath.replace(defaultPrefix +":", namespace)
    # add the element to the sequence
    toRemove = dom.find(xpath)
    toRemove.getparent().remove(toRemove)
    
    # save the tree in the session
    request.session['newXmlTemplateCompose'] = etree.tostring(dom) 
    
    return dajax.json()