"""
"""
from os.path import join
from mgi.models import FormElement, XMLElement, FormData, Module, Template
from mgi.settings import CURATE_MIN_TREE, CURATE_COLLAPSE
from bson.objectid import ObjectId
from mgi import common
from lxml import etree
import django.utils.html
from io import BytesIO
from modules import get_module_view
import urllib2

from mgi.common import LXML_SCHEMA_NAMESPACE, SCHEMA_NAMESPACE
from utils.XSDflattener.XSDflattener import XSDFlattenerURL


##################################################
# Part I: Utilities
##################################################
def get_subnodes_xpath(element, xml_tree):
    """Perform a lookup in subelements to build xpath

    Parameters:
        element: XML element
        xml_tree: xml_tree
    """
    # FIXME References returns the same object several times
    # TODO Check if min and maxOccurs are correctly reported (declared in ref but not reported elsewhere)
    xpaths = []

    if len(list(element)) > 0:
        for child in list(element):
            if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                if 'name' in child.attrib:
                    xpaths.append({'name': child.attrib['name'], 'element': child})
                elif 'ref' in child.attrib:
                    ref = child.attrib['ref']

                    if ':' in ref:
                        ref_split = ref.split(":")
                        ref_name = ref_split[1]
                        ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref_name))
                    else:
                        ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))

                    if ref_element is not None:
                        xpaths.append({'name': ref_element.attrib.get('name'), 'element': ref_element})
            else:
                xpaths.extend(get_subnodes_xpath(child, xml_tree))
    return xpaths


def get_nodes_xpath(elements, xml_tree):
    """Perform a lookup in subelements to build xpath.

    Get nodes' xpath, only one level deep. It's not going to every leaves. Only need to know if the
    node is here.

    Parameters:
        elements: XML element
        xml_tree: xml_tree
    """
    # FIXME Making one function with get_subnode_xpath should be possible, both are doing the same job
    # FIXME same problems as in get_subnodes_xpath
    xpaths = []

    for element in elements:
        if element.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
            if 'name' in element.attrib:
                xpaths.append({'name': element.attrib['name'], 'element': element})
            elif 'ref' in element.attrib:
                ref = element.attrib['ref']
                # ref_element = None
                if ':' in ref:
                    ref_split = ref.split(":")
                    ref_name = ref_split[1]
                    ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref_name))
                else:
                    ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))
                if ref_element is not None:
                    xpaths.append({'name': ref_element.attrib.get('name'), 'element': ref_element})
        else:
            xpaths.extend(get_subnodes_xpath(element, xml_tree))
    return xpaths


def lookup_occurs(request, element, xml_tree, full_path, edit_data_tree):
    """Do a lookup in data to get the number of occurences of a sequence or choice without a name (not within a named
    complextype).

    get the number of times the sequence appears in the XML document that we are loading for editing
    algorithm:
    get all the possible nodes that can appear in the sequence
    for each node, count how many times it's found in the data
    the maximum count is the number of occurrences of the sequence
    only works if data are determinist enough: means we don't have an element outside the sequence, and the same in
    the sequence

    Parameters:
        element: XML element
        xml_tree: xml_tree
        full_path: current node XPath
        edit_data_tree: XML data
    """
    # FIXME this function is not returning the correct output

    # get all possible xpaths of subnodes
    xpaths = get_nodes_xpath(element, xml_tree)
    max_occurs_found = 0

    # get target namespace prefix if one declared
    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
    target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_tree)
    if target_namespace_prefix != '':
        target_namespace_prefix += ":"

    # check if xpaths find a match in the document
    for xpath in xpaths:
        edit_elements = edit_data_tree.xpath(full_path + '/' + target_namespace_prefix + xpath['name'], namespaces=namespaces)

        if len(edit_elements) > max_occurs_found:
            max_occurs_found = 1

            if 'maxOccurs' in xpath['element'].attrib:
                if xpath['element'].attrib != "unbounded":
                    if xpath['element'].attrib < len(edit_elements):
                        # FIXME this part of code is not reachable (hence commented)
                        # max_occurs_found = len(edit_elements)

                        exc_mess = "These data can't be loaded for now, because of the following element: "
                        exc_mess += join(full_path, xpath['name'])  # XPath of the current element

                        raise Exception(exc_mess)

    return max_occurs_found


def manage_occurences(element):
    """Store information about the occurrences of the element

    Parameters:
        element: xsd element

    Returns:
        JSON data
    """
    min_occurs = 1
    max_occurs = 1

    if 'minOccurs' in element.attrib:
        min_occurs = float(element.attrib['minOccurs'])

    if 'maxOccurs' in element.attrib:
        if element.attrib['maxOccurs'] == "unbounded":
            max_occurs = float('inf')
        else:
            max_occurs = float(element.attrib['maxOccurs'])

    return min_occurs, max_occurs


def manage_attr_occurrences(element):
    """Store information about the occurrences of an attribute

    Parameters:
        element: XSD element

    Returns:
        JSON data
    """
    # FIXME attribute use defaults to optional not required

    min_occurs = 1
    max_occurs = 1

    if 'use' in element.attrib:
        if element.attrib['use'] == "optional":
            min_occurs = 0
        elif element.attrib['use'] == "prohibited":
            min_occurs = 0
            max_occurs = 0
        elif element.attrib['use'] == "required":
            pass

    return min_occurs, max_occurs


def render_buttons(add_button, delete_button, tag_id):
    """Displays buttons for a duplicable/removable element

    Parameters:
        add_button: boolean
        delete_button: boolean
        tag_id: id of the tag to associate buttons to it

    Returns:
        JSON data
    """
    add_button_type = type(add_button)
    del_button_type = type(delete_button)

    if add_button_type is not bool:
        raise TypeError('add_button type is wrong (' + str(add_button_type) + 'received, bool needed')

    if del_button_type is not bool:
        raise TypeError('add_button type is wrong (' + str(del_button_type) + 'received, bool needed')

    form_string = ""
    tag_id = str(tag_id)  # Tag ID string conversion

    # the number of occurrences is fixed, don't need buttons
    if not add_button and not delete_button:
        pass
    else:
        # FIXME remove onclick from buttons (use jquery instead)
        if add_button:
            form_string += "<span id='add" + tag_id + "' class='icon add' "
            form_string += "onclick=\"changeHTMLForm('add'," + tag_id + ");\"></span>"
        else:
            form_string += "<span id='add" + tag_id + "' class='icon add' "
            form_string += "style='display:none;' onclick=\"changeHTMLForm('add'," + tag_id + ");\"></span>"

        if delete_button:
            form_string += "<span id='remove" + tag_id + "' class='icon remove' "
            form_string += "onclick=\"changeHTMLForm('remove'," + tag_id + ");\"></span>"
        else:
            form_string += "<span id='remove" + tag_id + "' class='icon remove' "
            form_string += "style='display:none;' onclick=\"changeHTMLForm('remove'," + tag_id + ");\"></span>"

    return form_string


def has_module(request, element):
    """Look for a module in XML element's attributes

    Parameters:
        request: HTTP request
        element: XML element

    Returns:
        True: the element has a module attribute
        False: the element doesn't have a module attribute
    """
    # FIXME remove request (unused)
    _has_module = False

    # check if a module is set for this element
    if '{http://mdcs.ns}_mod_mdcs_' in element.attrib:
        # get the url of the module
        url = element.attrib['{http://mdcs.ns}_mod_mdcs_']
        # check that the url is registered in the system
        if url in Module.objects.all().values_list('url'):
            _has_module = True

    return _has_module


def get_xml_element_data(xsd_element, xml_element):
    """Return the content of an xml element

    Parameters:
        xsd_element:
        xml_element:
    Returns:
    """
    reload_data = None

    # get data
    if xsd_element.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
        # leaf: get the value
        if len(list(xml_element)) == 0:
            if xml_element.text is not None:
                reload_data = xml_element.text
            else:  # if xml_element.text is None
                reload_data = ''
        else:  # branch: get the whole branch
            reload_data = etree.tostring(xml_element)
    elif xsd_element.tag == "{0}attribute".format(LXML_SCHEMA_NAMESPACE):
        pass
    elif xsd_element.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE) or xsd_element.tag == "{0}simpleType".format(LXML_SCHEMA_NAMESPACE):
        # leaf: get the value
        if len(list(xml_element)) == 0:
            if xml_element.text is not None:
                reload_data = xml_element.text
            else:  # if xml_element.text is None
                reload_data = ''
        else:  # branch: get the whole branch
            try:
                reload_data = etree.tostring(xml_element)
            except:
                # FIXME in which case would we need that?
                reload_data = str(xml_element)

    return reload_data


def get_element_type(element, xml_tree, namespaces, default_prefix, target_namespace_prefix, schema_location=None):
    """get XSD type to render. Returns the tree where the type was found.

    Parameters:
        element: XML element
        xml_tree: XML tree of the template
        default_prefix:

    Returns:
                    Returns the type if found
                        - complexType
                        - simpleType
                    Returns None otherwise:
                        - type from default namespace (xsd:...)
                        - no type
                    Returns:
                        - tree where the type has been found
                        - schema location where the type has been found
    """

    element_type = None
    try:
        if 'type' not in element.attrib:  # element with type declared below it
            # if tag not closed:  <element/>
            if len(list(element)) == 1:
                if element[0].tag == "{0}annotation".format(LXML_SCHEMA_NAMESPACE):
                    element_type = None
                else:
                    element_type = element[0]
            # with annotations
            elif len(list(element)) == 2:
                # FIXME Not all possibilities are tested in this case
                element_type = element[1]
            else:
                element_type = None
        else:  # element with type attribute
            if element.attrib.get('type') in common.getXSDTypes(default_prefix):
                element_type = None
            elif element.attrib.get('type') is not None:  # FIXME is it possible?
                # TODO: manage namespaces
                # test if type of the element is a simpleType
                type_name = element.attrib.get('type')
                if ':' in type_name:
                    type_ns_prefix = type_name.split(":")[0]
                    type_name = type_name.split(":")[1]
                    if type_ns_prefix != target_namespace_prefix:
                        # TODO: manage ref to imported elements (different target namespace)
                        # get all import elements
                        imports = xml_tree.findall('//{}import'.format(LXML_SCHEMA_NAMESPACE))
                        # find the referred document using the prefix
                        for el_import in imports:
                            import_ns = el_import.attrib['namespace']
                            if namespaces[type_ns_prefix] == import_ns:
                                # get the location of the schema
                                ref_xml_schema_url = el_import.attrib['schemaLocation']
                                schema_location = ref_xml_schema_url
                                # download the file
                                ref_xml_schema_file = urllib2.urlopen(ref_xml_schema_url)
                                # read the content of the file
                                ref_xml_schema_content = ref_xml_schema_file.read()
                                # build the tree
                                xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                                # look for includes
                                includes = xml_tree.findall('//{}include'.format(LXML_SCHEMA_NAMESPACE))
                                # if includes are present
                                if len(includes) > 0:
                                    # create a flattener with the file content
                                    flattener = XSDFlattenerURL(ref_xml_schema_content)
                                    # flatten the includes
                                    ref_xml_schema_content = flattener.get_flat()
                                    # build the tree
                                    xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                                break

                xpath = "./{0}complexType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, type_name)
                element_type = xml_tree.find(xpath)
                if element_type is None:
                    # test if type of the element is a simpleType
                    xpath = "./{0}simpleType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, type_name)
                    element_type = xml_tree.find(xpath)
    except:
        print "get_element_type: Something went wrong"
        element_type = None
    return element_type, xml_tree, schema_location


def remove_annotations(element):
    """Remove annotations of an element if present

    Parameters:
        element: XML element
    """
    # FIXME annotation is not always the first child

    if len(list(element)) != 0:  # If element has children
        if element[0].tag == "{0}annotation".format(LXML_SCHEMA_NAMESPACE):  # If first child is annotation
            element.remove(element[0])


##################################################
# Part II: Schema parsing
##################################################

def generate_form(request):
    """Renders HTMl form for display.

    Parameters:
        request: HTTP request

    Returns:
        rendered HTMl form
    """

    # get the xsd tree when going back and forth with review step
    if 'xmlDocTree' in request.session:
        xml_doc_data = request.session['xmlDocTree']
    else:
        template_id = request.session['currentTemplateID']
        template_object = Template.objects.get(pk=template_id)
        xml_doc_data = template_object.content

    # flatten the includes
    flattener = XSDFlattenerURL(xml_doc_data)
    xml_doc_tree_str = flattener.get_flat()
    xml_doc_tree = etree.parse(BytesIO(xml_doc_tree_str.encode('utf-8')))

    request.session['xmlDocTree'] = xml_doc_tree_str

    # init counters
    request.session['nbChoicesID'] = '0'
    request.session['nb_html_tags'] = '0'

    # init id mapping structure (html/mongo)
    if 'mapTagID' in request.session:
        del request.session['mapTagID']
    request.session['mapTagID'] = {}

    form_string = ""

    # get form data from the database (empty one or existing one)
    form_data_id = request.session['curateFormData']
    form_data = FormData.objects.get(pk=ObjectId(form_data_id))

    # if editing, get the XML data to fill the form
    edit_data_tree = None
    if request.session['curate_edit']:
        # build the tree from data
        # transform unicode to str to support XML declaration
        if form_data.xml_data is not None:
            # Load a parser able to clean the XML from blanks, comments and processing instructions
            clean_parser = etree.XMLParser(remove_blank_text=True, remove_comments=True, remove_pis=True)
            # set the parser
            etree.set_default_parser(parser=clean_parser)
            # load the XML tree from the text
            edit_data_tree = etree.XML(str(form_data.xml_data.encode('utf-8')))
        else:  # no data found, not editing
            request.session['curate_edit'] = False

    # TODO: commented extensions Registry
    # # find extensions
    # request.session['extensions'] = get_extensions(request, xml_doc_tree, namespace, default_prefix)

    # find all root elements
    elements = xml_doc_tree.findall("./{0}element".format(LXML_SCHEMA_NAMESPACE))

    # try:
    # one root
    if len(elements) == 1:
        form_string += "<div xmlID='root' name='xsdForm'>"
        form_string += generate_element(request, elements[0], xml_doc_tree,
                                        edit_data_tree=edit_data_tree)
        form_string += "</div>"
    # multiple roots
    elif len(elements) > 1:
        form_string += "<div xmlID='root' name='xsdForm'>"
        form_string += generate_choice(request, elements, xml_doc_tree, edit_data_tree=edit_data_tree)
        form_string += "</div>"
    # except Exception, e:
    #     form_string = "UNSUPPORTED ELEMENT FOUND (" + e.message + ")"

    # save the list of elements for the form
    form_data.elements = request.session['mapTagID']
    # save data for the current form
    form_data.save()

    # delete temporary data structure for forms elements
    # TODO: use mongodb ids to avoid mapping
    del request.session['mapTagID']

    # data are loaded, switch Edit to False, we don't need to look at the original data anymore
    request.session['curate_edit'] = False

    return form_string


def generate_element(request, element, xml_tree, choice_info=None, full_path="",
                     edit_data_tree=None, schema_location=None):
    """Generate an HTML string that represents an XML element.

    Parameters:
        request: HTTP request
        element: XML element
        xml_tree: XML tree of the template
        choice_info:
        full_path:
        edit_data_tree:

    Returns:
        JSON data
    """
    # FIXME if elif without else need to be corrected
    # FIXME Support for unique is not present
    # FIXME Support for key / keyref
    form_string = ""

    # get appinfo elements
    app_info = common.getAppInfo(element)

    # check if the element has a module
    _has_module = has_module(request, element)

    # FIXME see if we can avoid these basic initialization
    # FIXME this is not necessarily true
    min_occurs = 1
    max_occurs = 1

    text_capitalized = ''
    element_tag = ''
    edit_elements = []
    ##############################################

    # check if XML element or attribute
    if element.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
        min_occurs, max_occurs = manage_occurences(element)
        element_tag = 'element'
    elif element.tag == "{0}attribute".format(LXML_SCHEMA_NAMESPACE):
        min_occurs, max_occurs = manage_attr_occurrences(element)
        element_tag = 'attribute'

    # get schema namespaces
    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))

    # get the name of the element, go find the reference if there's one
    if 'ref' in element.attrib:  # type is a reference included in the document
        ref = element.attrib['ref']
        # refElement = None
        if ':' in ref:
            # split the ref element
            ref_split = ref.split(":")
            # get the namespace prefix
            ref_namespace_prefix = ref_split[0]
            # get the element name
            ref_name = ref_split[1]
            # test if referencing element within the same schema (same target namespace)
            target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_tree)
            if target_namespace_prefix == ref_namespace_prefix:
                ref_element = xml_tree.find("./{0}{1}[@name='{2}']".format(LXML_SCHEMA_NAMESPACE,
                                                                           element_tag, ref_name))
            else:
                # TODO: manage ref to imported elements (different target namespace)
                # get all import elements
                imports = xml_tree.findall('//{}import'.format(LXML_SCHEMA_NAMESPACE))
                # find the referred document using the prefix
                for el_import in imports:
                    import_ns = el_import.attrib['namespace']
                    if namespaces[ref_namespace_prefix] == import_ns:
                        # get the location of the schema
                        ref_xml_schema_url = el_import.attrib['schemaLocation']
                        # set the schema location to save in database
                        schema_location = ref_xml_schema_url
                        # download the file
                        ref_xml_schema_file = urllib2.urlopen(ref_xml_schema_url)
                        # read the content of the file
                        ref_xml_schema_content = ref_xml_schema_file.read()
                        # build the tree
                        xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))
                        # look for includes
                        includes = xml_tree.findall('//{}include'.format(LXML_SCHEMA_NAMESPACE))
                        # if includes are present
                        if len(includes) > 0:
                            # create a flattener with the file content
                            flattener = XSDFlattenerURL(ref_xml_schema_content)
                            # flatten the includes
                            ref_xml_schema_content = flattener.get_flat()
                            # build the tree
                            xml_tree = etree.parse(BytesIO(ref_xml_schema_content.encode('utf-8')))

                        ref_element = xml_tree.find("./{0}{1}[@name='{2}']".format(LXML_SCHEMA_NAMESPACE,
                                                                                   element_tag, ref_name))
                        break
        else:
            ref_element = xml_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))

        if ref_element is not None:
            text_capitalized = ref_element.attrib.get('name')
            element = ref_element
            # check if the element has a module
            _has_module = has_module(request, element)
        else:
            # the element was not found where it was supposed to be
            # could be a use case too complex for the current parser
            print "Ref element not found" + str(element.attrib)
            return form_string
    else:
        text_capitalized = element.attrib.get('name')

    xml_tree_str = etree.tostring(xml_tree)
    namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
    target_namespace, target_namespace_prefix = common.get_target_namespace(namespaces, xml_tree)

    # build xpath
    # XML xpath:/root/element
    if element_tag == 'element':
        if target_namespace is not None:
            if target_namespace_prefix != '':
                if get_element_form_default(xml_tree) == "qualified":
                    full_path += '/{0}:{1}'.format(target_namespace_prefix, text_capitalized)
                elif "{1}:".format(target_namespace_prefix) in full_path:
                    full_path += '/{0}'.format(text_capitalized)
                else:
                    full_path += '/{0}:{1}'.format(target_namespace_prefix, text_capitalized)
            else:
                full_path += '/*[local-name()="{0}"]'.format(text_capitalized)
        else:
            full_path += "/{0}".format(text_capitalized)
    elif element_tag == 'attribute':
        if target_namespace is not None:
            if target_namespace_prefix != '':
                if get_attribute_form_default(xml_tree) == "qualified":
                    full_path += '/@{0}:{1}'.format(target_namespace_prefix, text_capitalized)
                elif "{0}:".format(target_namespace_prefix) in full_path:
                    full_path += '/@{0}'.format(text_capitalized)
                else:
                    full_path += '/@{0}:{1}'.format(target_namespace_prefix, text_capitalized)
            else:
                full_path += '/@*[local-name()="{0}"]'.format(text_capitalized)
        else:
            full_path += "/@{0}".format(text_capitalized)

    print full_path

    # XSD xpath: /element/complexType/sequence
    xsd_xpath = xml_tree.getpath(element)

    # init variables for buttons management
    add_button = False
    delete_button = False
    nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
    nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)
    # xml_element = None
    use = ""
    removed = False

    # loading data in the form
    if request.session['curate_edit']:
        # get the number of occurrences in the data
        edit_elements = edit_data_tree.xpath(full_path, namespaces=namespaces)
        nb_occurrences_data = len(edit_elements)

        if nb_occurrences_data == 0:
            use = "removed"
            removed = True

        # manage buttons
        if nb_occurrences_data < max_occurs:
            add_button = True
        if nb_occurrences_data > min_occurs:
            delete_button = True

    else:  # starting an empty form
        # Don't generate the element if not necessary
        if CURATE_MIN_TREE and min_occurs == 0:
            use = "removed"
            removed = True

        if nb_occurrences_data < max_occurs:
            add_button = True
        if nb_occurrences_data > min_occurs:
            delete_button = True

    if _has_module:
        # block maxOccurs to one, the module should take care of occurrences when the element is replaced
        nb_occurrences = 1
        max_occurs = 1
    elif nb_occurrences_data > nb_occurrences:
        nb_occurrences = nb_occurrences_data

    # get the element namespace
    element_ns = get_element_namespace(element, xml_tree)
    # set the element namespace
    tag_ns = ' xmlns="{0}" '.format(element_ns) if element_ns is not None else ''
    tag_ns_prefix = ''
    if element_tag == "attribute" and target_namespace is not None:
        for prefix, ns in namespaces.iteritems():
            if ns == target_namespace:
                tag_ns_prefix = ' ns_prefix="{0}" '.format(prefix)
                break

    # get the element type
    default_prefix = common.get_default_prefix(namespaces)
    element_type, xml_tree, schema_location = get_element_type(element, xml_tree, namespaces,
                                                               default_prefix, target_namespace_prefix,
                                                               schema_location)

    xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                             maxOccurs=max_occurs, schema_location=schema_location)
    xml_element.save()

    # management of elements inside a choice (don't display if not part of the currently selected choice)
    if choice_info:
        choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)

        if request.session['curate_edit']:
            if len(edit_elements) == 0:
                form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)
                    form_string += "</ul>"
                    return form_string
            else:
                form_string += "<ul id=\"" + choice_id + "\" >"
        else:
            if choice_info.counter > 0:
                form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)
                    form_string += "</ul>"
                    return form_string
            else:
                form_string += "<ul id=\"" + choice_id + "\" >"
    else:
        form_string += "<ul>"

    for x in range(0, int(nb_occurrences)):
        nb_html_tags = int(request.session['nb_html_tags'])
        tag_id = "element" + str(nb_html_tags)
        nb_html_tags += 1
        request.session['nb_html_tags'] = str(nb_html_tags)
        form_element = FormElement(html_id=tag_id, xml_element=xml_element, xml_xpath=full_path + '[' + str(x+1) + ']',
                                   name=text_capitalized).save()
        request.session['mapTagID'][tag_id] = str(form_element.id)

        # get the use from app info element
        app_info_use = app_info['use'] if 'use' in app_info else ''
        app_info_use = app_info_use if app_info_use is not None else ''
        use += ' ' + app_info_use

        # renders the name of the element
        form_string += "<li class='" + element_tag + ' ' + use + "' id='" + str(tag_id) + "' "
        form_string += 'tag="{0}" {1} {2}>'.format(django.utils.html.escape(text_capitalized),
                                                   tag_ns,
                                                   tag_ns_prefix)

        if CURATE_COLLAPSE:
            # the type is complex, can be collapsed
            if element_type is not None and element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                form_string += "<span class='collapse' style='cursor:pointer;' onclick='showhideCurate(event);'></span>"

        label = app_info['label'] if 'label' in app_info else text_capitalized
        label = label if label is not None else ''
        form_string += label
        # add buttons to add/remove elements
        buttons = ""
        if not (add_button is False and delete_button is False):
            buttons = render_buttons(add_button, delete_button, tag_id[7:])

        # get the default value (from xsd or from loaded xml)
        default_value = ""
        if request.session['curate_edit']:
            # if elements are found at this xpath
            if len(edit_elements) > 0:
                # it is an XML element
                if element_tag == 'element':
                    # get the value of the element x
                    if edit_elements[x].text is not None:
                        # set the value of the element
                        default_value = edit_elements[x].text
                # it is an XMl attribute
                elif element_tag == 'attribute':
                    # get the value of the attribute
                    if edit_elements[x] is not None:
                        # set the value of the element
                        default_value = str(edit_elements[x])
        elif 'default' in element.attrib:
            # if the default attribute is present
            default_value = element.attrib['default']

        # if element not removed
        if not removed:
            # if module is present, replace default input by module
            if _has_module:
                form_string += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                               edit_data_tree=edit_data_tree)
            else:  # generate the type
                if element_type is None:  # no complex/simple type
                    placeholder = 'placeholder="' + app_info['placeholder'] + '"' if 'placeholder' in app_info else ''
                    placeholder = placeholder if placeholder is not None else ''

                    tooltip = 'title="'+app_info['tooltip'] + '"' if 'tooltip' in app_info else ''
                    tooltip = tooltip if tooltip is not None else ''

                    form_string += " <input type='text' value='" + django.utils.html.escape(default_value) + "'"
                    form_string += placeholder + tooltip + "/>"
                    form_string += buttons
                else:  # complex/simple type
                    form_string += buttons

                    if element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                        form_string += generate_complex_type(request, element_type, xml_tree,
                                                             full_path=full_path+'[' + str(x+1) + ']',
                                                             edit_data_tree=edit_data_tree,
                                                             schema_location=schema_location)
                    elif element_type.tag == "{0}simpleType".format(LXML_SCHEMA_NAMESPACE):
                        form_string += generate_simple_type(request, element_type, xml_tree,
                                                            full_path=full_path+'[' + str(x+1) + ']',
                                                            edit_data_tree=edit_data_tree, default_value=default_value,
                                                            schema_location=schema_location)
        else:
            form_string += buttons

        form_string += "</li>"
    form_string += "</ul>"

    return form_string


def get_element_form_default(xsd_tree):

    # default value
    element_form_default = "unqualified"

    root = xsd_tree.getroot()
    if 'elementFormDefault' in root.attrib:
        element_form_default = root.attrib['elementFormDefault']

    return element_form_default


def get_attribute_form_default(xsd_tree):

    # default value
    attribute_form_default = "unqualified"

    root = xsd_tree.getroot()
    if 'attributeFormDefault' in root.attrib:
        attribute_form_default = root.attrib['attributeFormDefault']

    return attribute_form_default


def get_element_namespace(element, xsd_tree):
    """
    get_element_tag
    :param element:
    :param xsd_tree:
    :param is_root:
    :return:
    """
    # get the root of the XSD document
    xsd_root = xsd_tree.getroot()

    # None by default, None means no namespace information needed, different from empty namespace
    element_ns = None

    # check if the element is root
    is_root = False
    # get XSD xpath
    xsd_path = xsd_tree.getpath(element)
    # the element is global (/xs:schema/xs:element)
    if xsd_path.count('/') == 2:
        is_root = True

    # root is always qualified, root from other schemas too
    if is_root:
        # if in a targetNamespace
        if 'targetNamespace' in xsd_root.attrib:
            # get the target namespace
            target_namespace = xsd_root.attrib['targetNamespace']
            element_ns = target_namespace
    else:
        # qualified elements
        if 'elementFormDefault' in xsd_root.attrib and xsd_root.attrib['elementFormDefault'] == 'qualified'\
                or 'attributeFormDefault' in xsd_root.attrib and xsd_root.attrib['attributeFormDefault'] == 'qualified':
            if 'targetNamespace' in xsd_root.attrib:
                # get the target namespace
                target_namespace = xsd_root.attrib['targetNamespace']
                element_ns = target_namespace
        # unqualified elements
        else:
            if 'targetNamespace' in xsd_root.attrib:
                element_ns = ""

    # print tag_ns
    return element_ns


def generate_element_absent(request, element, xml_doc_tree, form_element, schema_location=None):
    """
    # Inputs:        request -
    # Outputs:       JSON data
    # Exceptions:    None
    # Description:   Generate XML element for which the element is absent from the form
    Parameters:
        request:
        element:
        xml_doc_tree:
        form_element:

    Returns:
    """
    # TODO see if it is possibe to group with generate_element
    form_string = ""

    # get appinfo elements
    app_info = common.getAppInfo(element)

    # check if the element has a module
    _has_module = has_module(request, element)

    # type is a reference included in the document
    if 'ref' in element.attrib:
        ref = element.attrib['ref']
        # refElement = None

        if ':' in ref:
            ref_split = ref.split(":")
            ref_name = ref_split[1]
            ref_element = xml_doc_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref_name))
        else:
            ref_element = xml_doc_tree.find("./{0}element[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, ref))

        if ref_element is not None:
            element = ref_element
            # check if the element has a module
            _has_module = has_module(request, element)

    if _has_module:
        form_string += generate_module(request, element, form_element.xml_element.xsd_xpath,
                                       form_element.xml_xpath, xml_tree=xml_doc_tree)
    else:
        xml_tree_str = etree.tostring(xml_doc_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        default_prefix = common.get_default_prefix(namespaces)
        target_namespace_prefix = common.get_target_namespace_prefix(namespaces, xml_doc_tree)
        element_type, xml_doc_tree, schema_location = get_element_type(element, xml_doc_tree, namespaces,
                                                                       default_prefix, target_namespace_prefix,
                                                                       schema_location)

        # render the type
        if element_type is None:  # no complex/simple type
            default_value = ""

            if 'default' in element.attrib:
                # if the default attribute is present
                default_value = element.attrib['default']

            placeholder = 'placeholder="' + app_info['placeholder'] + '"' if 'placeholder' in app_info else ''
            placeholder = placeholder if placeholder is not None else ''

            tooltip = 'title="' + app_info['tooltip'] + '"' if 'tooltip' in app_info else ''
            tooltip = tooltip if tooltip is not None else ''

            form_string += " <input type='text' value='" + django.utils.html.escape(default_value) + "'"
            form_string += placeholder + tooltip + "/>"
        else:  # complex/simple type
            if element_type.tag == "{0}complexType".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_complex_type(request, element_type, xml_doc_tree,
                                                     full_path=form_element.xml_xpath, schema_location=schema_location)
            elif element_type.tag == "{0}simpleType".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_simple_type(request, element_type, xml_doc_tree,
                                                    full_path=form_element.xml_xpath, schema_location=schema_location)

    return form_string


def generate_sequence(request, element, xml_tree, choice_info=None, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML sequence

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        choice_info:
        full_path:
        edit_data_tree:

    Returns:       HTML string representing a sequence
    """
    # (annotation?,(element|group|choice|sequence|any)*)
    # FIXME implement group, any
    form_string = ""

    # remove the annotations
    remove_annotations(element)

    min_occurs, max_occurs = manage_occurences(element)

    # if sequences can be deleted or duplicated
    if (min_occurs != 1) or (max_occurs != 1):
        text = "Sequence"

        # XSD xpath
        xsd_xpath = xml_tree.getpath(element)

        # init variables for buttons management
        add_button = False
        delete_button = False
        nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)
        # xml_element = None

        # loading data in the form
        if request.session['curate_edit']:
            # get the number of occurrences in the data
            nb_occurrences_data = lookup_occurs(request, element, xml_tree, full_path, edit_data_tree)

            # manage buttons
            if nb_occurrences_data < max_occurs:
                add_button = True
            if nb_occurrences_data > min_occurs:
                delete_button = True
        else:  # starting an empty form
            # Don't generate the element if not necessary
            if CURATE_MIN_TREE and min_occurs == 0:
                add_button = True
                delete_button = False
            else:
                if nb_occurrences_data < max_occurs:
                    add_button = True
                if nb_occurrences_data > min_occurs:
                    delete_button = True

        if nb_occurrences_data > nb_occurrences:
            nb_occurrences = nb_occurrences_data

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs, schema_location=schema_location).save()

        # keeps track of elements to display depending on the selected choice
        if choice_info:
            choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)
            if request.session['curate_edit']:
                if nb_occurrences == 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"
            else:
                if choice_info.counter > 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"
        else:
            form_string += "<ul>"

        # editing data and sequence not found in data
        if nb_occurrences_data == 0:
            nb_html_tags = int(request.session['nb_html_tags'])
            tag_id = "element" + str(nb_html_tags)
            nb_html_tags += 1
            request.session['nb_html_tags'] = str(nb_html_tags)
            form_element = FormElement(html_id=tag_id, xml_element=xml_element, xml_xpath=full_path + '[1]').save()
            request.session['mapTagID'][tag_id] = str(form_element.id)
            form_string += "<li class='sequence removed' id='" + str(tag_id) + "'>"

            if CURATE_COLLAPSE:
                form_string += "<span class='collapse' style='cursor:pointer;' onclick='showhideCurate(event);'></span>"

            form_string += text
            form_string += "<span id='add" + str(tag_id[7:]) + "' class=\"icon add\" onclick=\"changeHTMLForm('add',"
            form_string += str(tag_id[7:])+");\"></span>"
            form_string += "<span id='remove" + str(tag_id[7:]) + "' class=\"icon remove\" style=\"display:none;\" "
            form_string += "onclick=\"changeHTMLForm('remove'," + str(tag_id[7:]) + ");\"></span>"
        else:
            for x in range(0, int(nb_occurrences)):
                nb_html_tags = int(request.session['nb_html_tags'])
                tag_id = "element" + str(nb_html_tags)
                nb_html_tags += 1
                request.session['nb_html_tags'] = str(nb_html_tags)
#                 if (minOccurs != 1) or (maxOccurs != 1):
                form_element = FormElement(html_id=tag_id, xml_element=xml_element,
                                           xml_xpath=full_path + '[' + str(x+1) + ']')
                form_element.save()
                request.session['mapTagID'][tag_id] = str(form_element.pk)

                # if tag not closed:  <element/>
                if len(list(element)) > 0:
                    form_string += "<li class='sequence' id='" + str(tag_id) + "'>"

                    if CURATE_COLLAPSE:
                        form_string += "<span class='collapse' style='cursor:pointer;' "
                        form_string += "onclick='showhideCurate(event);'></span>"

                    form_string += text
                else:
                    form_string += "<li class='sequence' id='" + str(tag_id) + "'>" + text

                if add_button:
                    form_string += "<span id='add" + str(tag_id[7:])
                    form_string += "' class=\"icon add\" onclick=\"changeHTMLForm('add',"+str(tag_id[7:])+");\"></span>"
                else:
                    form_string += "<span id='add" + str(tag_id[7:]) + "' class=\"icon add\" style=\"display:none;\" "
                    form_string += "onclick=\"changeHTMLForm('add'," + str(tag_id[7:]) + ");\"></span>"

                if delete_button:
                    form_string += "<span id='remove" + str(tag_id[7:]) + "' class=\"icon remove\" "
                    form_string += "onclick=\"changeHTMLForm('remove',"+str(tag_id[7:])+");\"></span>"
                else:
                    form_string += "<span id='remove" + str(tag_id[7:]) + "' class=\"icon remove\" "
                    form_string += "style=\"display:none;\" "
                    form_string += "onclick=\"changeHTMLForm('remove'," + str(tag_id[7:]) + ");\">"
                    form_string += "</span>"

                # generates the sequence
                if len(list(element)) != 0:
                    for child in element:
                        if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                            form_string += generate_element(request, child, xml_tree, choice_info,
                                                            full_path=full_path, edit_data_tree=edit_data_tree,
                                                            schema_location=schema_location)
                        elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                            form_string += generate_sequence(request, child, xml_tree, choice_info,
                                                             full_path=full_path, edit_data_tree=edit_data_tree,
                                                             schema_location=schema_location)
                        elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                            form_string += generate_choice(request, child, xml_tree, choice_info,
                                                           full_path=full_path, edit_data_tree=edit_data_tree,
                                                           schema_location=schema_location)
                        elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                            pass
                        elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                            pass
                form_string += "</li>"
        form_string += "</ul>"
    else:
        # XSD xpath
        xsd_xpath = xml_tree.getpath(element)

        # init variables for buttons management
        nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs, schema_location=schema_location).save()

        if choice_info:
            choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)
            if request.session['curate_edit']:
                if nb_occurrences == 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"
            else:
                if choice_info.counter > 0:
                    form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"
                    if CURATE_MIN_TREE:
                        form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                        request.session['mapTagID'][choice_id] = str(form_element.id)
                        form_string += "</ul>"
                        return form_string
                else:
                    form_string += "<ul id=\"" + choice_id + "\" >"

        # generates the sequence
        if len(list(element)) != 0:
            for child in element:
                if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                    form_string += generate_element(request, child, xml_tree, choice_info,
                                                    full_path=full_path, edit_data_tree=edit_data_tree,
                                                    schema_location=schema_location)
                elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                    form_string += generate_sequence(request, child, xml_tree, choice_info,
                                                     full_path=full_path, edit_data_tree=edit_data_tree,
                                                     schema_location=schema_location)
                elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                    form_string += generate_choice(request, child, xml_tree, choice_info,
                                                   full_path=full_path, edit_data_tree=edit_data_tree,
                                                   schema_location=schema_location)
                elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                    pass
                elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                    pass
        # close the list
        if choice_info:
            form_string += "</ul>"
    return form_string


def generate_sequence_absent(request, element, xml_tree, schema_location=None):
    """Generates a section of the form that represents an XML sequence

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
    Returns:
        HTML string representing a sequence
    """
    # TODO see if it can be merged in generate_sequence
    form_string = ""

    # generates the sequence
    if len(list(element)) != 0:
        for child in element:
            if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_element(request, child, xml_tree, schema_location=schema_location)
            elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_sequence(request, child, xml_tree, schema_location=schema_location)
            elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_choice(request, child, xml_tree, schema_location=schema_location)
            elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                pass

    return form_string


def generate_choice(request, element, xml_tree, choice_info=None, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML choice

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        choice_info: to keep track of branches to display (chosen ones) when going recursively down the tree
        full_path: XML xpath being built
        edit_data_tree: XML tree of data being edited

    Returns:       HTML string representing a sequence
    """
    # (annotation?,(element|group|choice|sequence|any)*)
    # FIXME Group not supported
    # FIXME Choice not supported
    form_string = ""

    # remove the annotations
    remove_annotations(element)

    # init variables for buttons management
    add_button = False
    delete_button = False
    nb_occurrences = 1  # nb of occurrences to render (can't be 0 or the user won't see this element at all)
    nb_occurrences_data = 1
    xml_element = None

    # not multiple roots
    if not isinstance(element, list):
        # XSD xpath: don't need it when multiple root (can't duplicate a root)
        xsd_xpath = xml_tree.getpath(element)

        # get element's min/max occurs attributes
        min_occurs, max_occurs = manage_occurences(element)
        nb_occurrences_data = min_occurs  # nb of occurrences in loaded data or in form being rendered (can be 0)

        # loading data in the form
        if request.session['curate_edit']:
            # get the number of occurrences in the data
            nb_occurrences_data = lookup_occurs(request, element, xml_tree, full_path, edit_data_tree)

            if nb_occurrences_data < max_occurs:
                add_button = True
            if nb_occurrences_data > min_occurs:
                delete_button = True
        else:  # starting an empty form
            # Don't generate the element if not necessary
            if CURATE_MIN_TREE and min_occurs == 0:
                add_button = True
                delete_button = False
            else:
                if nb_occurrences_data < max_occurs:
                    add_button = True
                if nb_occurrences_data > min_occurs:
                    delete_button = True

        if nb_occurrences_data > nb_occurrences:
            nb_occurrences = nb_occurrences_data

        xml_element = XMLElement(xsd_xpath=xsd_xpath, nbOccurs=nb_occurrences_data, minOccurs=min_occurs,
                                 maxOccurs=max_occurs,schema_location=schema_location)
        xml_element.save()

    # keeps track of elements to display depending on the selected choice
    if choice_info:
        choice_id = choice_info.chooseIDStr + "-" + str(choice_info.counter)

        if request.session['curate_edit']:
            if nb_occurrences == 0:
                form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)
                    form_string += "</ul>"
                    return form_string
            else:
                form_string += "<ul id=\"" + choice_id + "\" >"
        else:
            if choice_info.counter > 0:
                form_string += "<ul id=\"" + choice_id + "\" class=\"notchosen\">"

                if CURATE_MIN_TREE:
                    form_element = FormElement(html_id=choice_id, xml_element=xml_element, xml_xpath=full_path).save()
                    request.session['mapTagID'][choice_id] = str(form_element.id)
                    form_string += "</ul>"
                    return form_string
            else:
                form_string += "<ul id=\"" + choice_id + "\" >"
    else:
        form_string += "<ul>"

    for x in range(0, int(nb_occurrences)):
        nb_html_tags = int(request.session['nb_html_tags'])
        tag_id = "element" + str(nb_html_tags)
        nb_html_tags += 1
        request.session['nb_html_tags'] = str(nb_html_tags)

        form_element = FormElement(html_id=tag_id, xml_element=xml_element,
                                   xml_xpath=full_path + '[' + str(x+1) + ']')
        form_element.save()

        request.session['mapTagID'][tag_id] = str(form_element.pk)

        nb_choices_id = int(request.session['nbChoicesID'])
        choose_id = nb_choices_id
        choose_id_str = 'choice' + str(choose_id)
        nb_choices_id += 1

        request.session['nbChoicesID'] = str(nb_choices_id)

        if nb_occurrences_data == 0:
            form_string += "<li class='choice removed' id='" + str(tag_id) + "'>Choose"
            form_string += "<select id='" + choose_id_str + "' "
            form_string += "onchange=\"changeChoice(this);\">"
        else:
            form_string += "<li class='choice' id='" + str(tag_id) + "'>Choose<select id='" + choose_id_str + "' "
            form_string += "onchange=\"changeChoice(this);\">"

        nb_sequence = 1

        # generates the choice
        if len(list(element)) != 0:
            for child in element:
                if child.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                    if child.attrib.get('name') is not None:
                        opt_value = opt_label = child.attrib.get('name')
                    else:
                        opt_value = opt_label = child.attrib.get('ref')

                        if ':' in opt_label:
                            opt_label = opt_label.split(':')[1]

                    # look for active choice when editing
                    element_path = full_path + '/' + opt_label

                    if request.session['curate_edit']:
                        # get the schema namespaces
                        xml_tree_str = etree.tostring(xml_tree)
                        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
                        if len(edit_data_tree.xpath(element_path, namespaces=namespaces)) == 0:
                            form_string += "<option value='" + opt_value + "'>" + opt_label + "</option><br/>"
                        else:
                            form_string += "<option value='" + opt_value + "' selected='selected'>" + opt_label
                            form_string += "</option><br/>"
                    else:
                        form_string += "<option value='" + opt_value + "'>" + opt_label + "</option><br/>"
                elif child.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                    pass
                elif child.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                    pass
                elif child.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                    form_string += "<option value='sequence" + str(nb_sequence) + "'>Sequence " + str(nb_sequence)
                    form_string += "</option><br/>"
                    nb_sequence += 1
                elif child.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                    pass

        form_string += "</select>"

        if add_button:
            form_string += "<span id='add" + str(tag_id[7:]) + "' class=\"icon add\" "
            form_string += "onclick=\"changeHTMLForm('add'," + str(tag_id[7:]) + ");\"></span>"
        else:
            form_string += "<span id='add" + str(tag_id[7:]) + "' class=\"icon add\" style=\"display:none;\" "
            form_string += "onclick=\"changeHTMLForm('add',"+str(tag_id[7:])+");\"></span>"

        if delete_button:
            form_string += "<span id='remove" + str(tag_id[7:]) + "' class=\"icon remove\" "
            form_string += "onclick=\"changeHTMLForm('remove',"+str(tag_id[7:])+");\"></span>"
        else:
            form_string += "<span id='remove" + str(tag_id[7:]) + "' class=\"icon remove\" style=\"display:none;\" "
            form_string += "onclick=\"changeHTMLForm('remove'," + str(tag_id[7:]) + ");\"></span>"

        for (counter, choiceChild) in enumerate(list(element)):
            if choiceChild.tag == "{0}element".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_element(request, choiceChild, xml_tree,
                                                common.ChoiceInfo(choose_id_str, counter), full_path=full_path,
                                                edit_data_tree=edit_data_tree, schema_location=schema_location)
            elif choiceChild.tag == "{0}group".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif choiceChild.tag == "{0}choice".format(LXML_SCHEMA_NAMESPACE):
                pass
            elif choiceChild.tag == "{0}sequence".format(LXML_SCHEMA_NAMESPACE):
                form_string += generate_sequence(request, choiceChild, xml_tree,
                                                 common.ChoiceInfo(choose_id_str, counter), full_path=full_path,
                                                 edit_data_tree=edit_data_tree, schema_location=schema_location)
            elif choiceChild.tag == "{0}any".format(LXML_SCHEMA_NAMESPACE):
                pass

        form_string += "</li>"
    form_string += "</ul>"

    return form_string


def generate_simple_type(request, element, xml_tree, full_path, edit_data_tree=None,
                         default_value=None, schema_location=None):
    """Generates a section of the form that represents an XML simple type

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a simple type
    """
    # FIXME implement union, correct list
    form_string = ""

    # remove the annotations
    remove_annotations(element)

    if has_module(request, element):
        # XSD xpath: /element/complexType/sequence
        xsd_xpath = xml_tree.getpath(element)
        form_string += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                       edit_data_tree=edit_data_tree)
        return form_string

    if list(element) != 0:
        child = element[0]

        if child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE):
            form_string += generate_restriction(request, child, xml_tree, full_path, edit_data_tree=edit_data_tree,
                                                default_value=default_value, schema_location=schema_location)
        elif child.tag == "{0}list".format(LXML_SCHEMA_NAMESPACE):
            # TODO list can contain a restriction/enumeration
            default_value = default_value if default_value is not None else ''
            form_string += " <input type='text' value='" + django.utils.html.escape(default_value) + "'/>"
        elif child.tag == "{0}union".format(LXML_SCHEMA_NAMESPACE):
            # TODO: provide UI for unions
            default_value = default_value if default_value is not None else ''
            form_string += " <input type='text' value='" + django.utils.html.escape(default_value) + "'/>"

    return form_string


def generate_complex_type(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML complexType

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a sequence
    """
    # FIXME add support for complexContent, group, attributeGroup, anyAttribute
    # (
    #   annotation?,
    #   (
    #       simpleContent|complexContent|(
    #           (group|all|choice|sequence)?,
    #           (
    #               (attribute|attributeGroup)*,
    #               anyAttribute?
    #           )
    #       )
    #   )
    # )

    formString = ""

    # remove the annotations
    remove_annotations(element)

    if has_module(request, element):
        # XSD xpath: /element/complexType/sequence
        xsd_xpath = xml_tree.getpath(element)
        formString += generate_module(request, element, xsd_xpath, full_path, xml_tree=xml_tree,
                                      edit_data_tree=edit_data_tree)
        return formString

    # is it a simple content?
    complexTypeChild = element.find('{0}simpleContent'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        formString += generate_simple_content(request, complexTypeChild, xml_tree, full_path=full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)
        return formString

    # is it a complex content?
    complexTypeChild = element.find('{0}complexContent'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        formString += generate_complex_content(request, complexTypeChild, xml_tree, full_path=full_path,
                                               edit_data_tree=edit_data_tree, schema_location=schema_location)
        return formString

    # does it contain any attributes?
    complexTypeChildren = element.findall('{0}attribute'.format(LXML_SCHEMA_NAMESPACE))
    if len(complexTypeChildren) > 0:
        for attribute in complexTypeChildren:
            formString += generate_element(request, attribute, xml_tree, full_path=full_path,
                                           edit_data_tree=edit_data_tree, schema_location=schema_location)

    # does it contain sequence or all?
    complexTypeChild = element.find('{0}sequence'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        formString += generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                        edit_data_tree=edit_data_tree, schema_location=schema_location)
    else:
        complexTypeChild = element.find('{0}all'.format(LXML_SCHEMA_NAMESPACE))
        if complexTypeChild is not None:
            formString += generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                            edit_data_tree=edit_data_tree, schema_location=schema_location)
        else:
            # does it contain choice ?
            complexTypeChild = element.find('{0}choice'.format(LXML_SCHEMA_NAMESPACE))
            if complexTypeChild is not None:
                formString += generate_choice(request, complexTypeChild, xml_tree, full_path=full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)
            else:
                formString += ""

    # TODO: commented extensions Registry
    # # check if the type has a name (for reference)
    # if 'name' in element.attrib:
    #     # check if types extend this one
    #     extensions = request.session['extensions']
    #
    #     # the complextype has some possible extensions
    #     if element.attrib['name'] in extensions.keys():
    #         # get all extensions associated with the type
    #         current_type_extensions = extensions[element.attrib['name']]
    #
    #         # build namesapces to use with xpath
    #         xpath_namespaces = {}
    #         for prefix, ns in request.session['namespaces'].iteritems() :
    #             xpath_namespaces[prefix] = ns[1:-1]
    #
    #         # get extension types using XPath
    #         extension_types = []
    #         for current_type_extension in current_type_extensions:
    #             # get the extension using its xpath
    #             extension_element = xml_tree.xpath(current_type_extension, namespaces=xpath_namespaces)[0]
    #             extension_types.append(extension_element)
    #
    #
    #         formString += '<div class="extension">'
    #         formString += 'Extend <select onchange="changeExtension()">'
    #         formString += '<option> --------- </option>'
    #
    #         # browse extension types
    #         for extension_type in extension_types:
    #             formString += '<option>'
    #             # get the closest type name: parent -> xxxContent, parent -> xxxType
    #             formString += extension_type.getparent().getparent().attrib['name']
    #             formString += '</option>'
    #
    #         formString += '</select>'
    #         formString += '</div>'
    #         # if extension_element.tag == "{0}complexType".format(namespace):
    #         #     pass
    #         # elif extension_element.tag == "{0}simpleType".format(namespace):
    #         #     pass
    return formString


def generate_complex_content(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """
    Inputs:        request -
                   element - XML element
                   xmlTree - XML Tree
    Outputs:       HTML string representing a sequence
    Exceptions:    None
    Description:   Generates a section of the form that represents an XML complex content
    :param request:
    :param element:
    :param xmlTree:
    :param fullPath:
    :param edit_data_tree:
    :return:
    """
    #(annotation?,(restriction|extension))

    form_string = ""

    # remove the annotations
    remove_annotations(element)

    # generates the content
    if(len(list(element)) != 0):
        child = element[0]
        if (child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE)):
            form_string += generate_restriction(request, child, xml_tree, full_path,
                                                edit_data_tree=edit_data_tree, schema_location=schema_location)
        elif (child.tag == "{0}extension".format(LXML_SCHEMA_NAMESPACE)):
            form_string += generate_extension(request, child, xml_tree, full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)

    return form_string


def generate_module(request, element, xsd_xpath=None, xml_xpath=None, xml_tree=None, edit_data_tree=None):
    """Generate a module to replace an element

    Parameters:
        request:
        element:
        xsd_xpath:
        xml_xpath:
        edit_data_tree:

    Returns:
        Module
    """
    form_string = ""
    reload_data = None
    reload_attrib = None
    
    if request.session['curate_edit']:
        # get the schema namespaces
        xml_tree_str = etree.tostring(xml_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        edit_elements = edit_data_tree.xpath(xml_xpath, namespaces=namespaces)
        
        if len(edit_elements) > 0:
            if len(edit_elements) == 1:
                edit_element = edit_elements[0]
                
                # get attributes
                if 'attribute' not in xsd_xpath and len(edit_element.attrib) > 0:
                    reload_attrib = dict(edit_element.attrib)
                    
                reload_data = get_xml_element_data(element, edit_element)
            else:
                reload_data = []
                reload_attrib = []
                
                for edit_element in edit_elements:
                    reload_attrib.append(dict(edit_element.attrib))
                    reload_data.append(get_xml_element_data(element, edit_element))

    # check if a module is set for this element
    if '{http://mdcs.ns}_mod_mdcs_' in element.attrib:
        # get the url of the module
        url = element.attrib['{http://mdcs.ns}_mod_mdcs_']
        
        # check that the url is registered in the system
        if url in Module.objects.all().values_list('url'):
            view = get_module_view(url)

            # build a request to send to the module to initialize it
            mod_req = request
            mod_req.method = 'GET'

            mod_req.GET = {
                'url': url,
                'xsd_xpath': xsd_xpath,
                'xml_xpath': xml_xpath,
            }

            # if the loaded doc has data, send them to the module for initialization
            if reload_data is not None:
                mod_req.GET['data'] = reload_data
                
            if reload_attrib is not None:
                mod_req.GET['attributes'] = reload_attrib

            # renders the module
            form_string += view(mod_req).content.decode("utf-8")

    return form_string


def generate_simple_content(request, element, xml_tree, full_path, edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML simple content

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a simple content
    """
    # (annotation?,(restriction|extension))
    # FIXME better support for extension

    form_string = ""

    # remove the annotations
    remove_annotations(element)

    # generates the content
    if len(list(element)) != 0:
        child = element[0]

        if child.tag == "{0}restriction".format(LXML_SCHEMA_NAMESPACE):
            form_string += generate_restriction(request, child, xml_tree, full_path,
                                                edit_data_tree=edit_data_tree, schema_location=schema_location)
        elif child.tag == "{0}extension".format(LXML_SCHEMA_NAMESPACE):
            form_string += generate_extension(request, child, xml_tree, full_path,
                                              edit_data_tree=edit_data_tree, schema_location=schema_location)

    return form_string


def generate_restriction(request, element, xml_tree, full_path="", edit_data_tree=None,
                         default_value=None, schema_location=None):
    """Generates a section of the form that represents an XML restriction

    Parameters:
        request:
        element: XML element
        xml_tree: XML Tree
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing a sequence
    """
    # FIXME doesn't represent all the possibilities (http://www.w3schools.com/xml/el_restriction.asp)
    form_string = ""

    remove_annotations(element)

    enumeration = element.findall('{0}enumeration'.format(LXML_SCHEMA_NAMESPACE))

    if len(enumeration) > 0:
        form_string += "<select>"

        if request.session['curate_edit']:
            default_value = default_value if default_value is not None else ''
            for enum in enumeration:
                if default_value is not None and enum.attrib.get('value') == default_value:
                    form_string += "<option value='" + enum.attrib.get('value') + "' selected='selected'>"
                    form_string += enum.attrib.get('value') + "</option>"
                else:
                    form_string += "<option value='" + enum.attrib.get('value') + "'>" + enum.attrib.get('value')
                    form_string += "</option>"
        else:
            for enum in enumeration:
                form_string += "<option value='" + enum.attrib.get('value') + "'>" + enum.attrib.get('value')
                form_string += "</option>"

        form_string += "</select>"
    else:
        simple_type = element.find('{0}simpleType'.format(LXML_SCHEMA_NAMESPACE))
        if simple_type is not None:
            form_string += generate_simple_type(request, simple_type, xml_tree, full_path=full_path,
                                                edit_data_tree=edit_data_tree, default_value=default_value,
                                                schema_location=schema_location)
        else:
            default_value = default_value if default_value is not None else ''
            form_string += " <input type='text' value='{0}'/>".format(default_value)

    return form_string

# TODO: commented extensions Registry
# def get_extensions(request, xml_doc_tree, default_prefix):
#     """Get all XML extensions of the XML Schema
#
#     Parameters:
#         request:
#         element:
#         xml_tree:
#         full_path:
#         edit_data_tree:
#
#     Returns:
#         HTML string representing an extension
#     """
#     # get all extensions of the document
#     extensions = xml_doc_tree.findall(".//{0}extension".format(LXML_SCHEMA_NAMESPACE))
#     # keep only simple/complex type extensions, no built-in types
#     custom_type_extensions = {}
#     for extension in extensions:
#         base = extension.attrib['base']
#         if base not in common.getXSDTypes(default_prefix):
#             if base not in custom_type_extensions.keys():
#                 custom_type_extensions[base] = []
#             custom_type_extensions[base].append(etree.ElementTree(xml_doc_tree).getpath(extension))
#
#     return custom_type_extensions


def generate_extension(request, element, xml_tree, full_path="", edit_data_tree=None, schema_location=None):
    """Generates a section of the form that represents an XML extension

    Parameters:
        request:
        element:
        xml_tree:
        full_path:
        edit_data_tree:

    Returns:
        HTML string representing an extension
    """
    # FIXME doesn't represent all the possibilities (http://www.w3schools.com/xml/el_extension.asp)
    form_string = ""

    remove_annotations(element)

    # get the base attibute being extended
    if 'base' in element.attrib:
        base = element.attrib['base']

        xml_tree_str = etree.tostring(xml_tree)
        namespaces = common.get_namespaces(BytesIO(str(xml_tree_str)))
        default_prefix = common.get_default_prefix(namespaces)

        # test if base is a built-in data types
        if base in common.getXSDTypes(default_prefix):
            pass
            #form_string +=
        else: #not a built-in data type
            if ':' in base:
                splittedBase = base.split(":")
                baseNSPrefix = splittedBase[0]
                baseName = splittedBase[1]
                # namespaces = request.session['namespaces']
                # TODO: look at namespaces, target namespaces
                # baseNS = namespaces[baseNSPrefix]
            else:
                baseName = base

            # test if base is a simple type
            baseType = xml_tree.find(".//{0}simpleType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, baseName))
            if baseType is not None:
                form_string += generate_simple_type(request, baseType, xml_tree, full_path,
                                                    edit_data_tree, schema_location=schema_location)
            else:
                # test if base is a complex type
                baseType = xml_tree.find(".//{0}complexType[@name='{1}']".format(LXML_SCHEMA_NAMESPACE, baseName))
                if baseType is not None:
                    form_string += generate_complex_type(request, baseType, xml_tree, full_path,
                                                         edit_data_tree, schema_location=schema_location)

    # does it contain any attributes?
    complexTypeChildren = element.findall('{0}attribute'.format(LXML_SCHEMA_NAMESPACE))
    if len(complexTypeChildren) > 0:
        for attribute in complexTypeChildren:
            form_string += generate_element(request, attribute, xml_tree, full_path=full_path,
                                            edit_data_tree=edit_data_tree, schema_location=schema_location)

    # does it contain sequence or all?
    complexTypeChild = element.find('{0}sequence'.format(LXML_SCHEMA_NAMESPACE))
    if complexTypeChild is not None:
        form_string += generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                         edit_data_tree=edit_data_tree, schema_location=schema_location)
    else:
        complexTypeChild = element.find('{0}all'.format(LXML_SCHEMA_NAMESPACE))
        if complexTypeChild is not None:
            form_string += generate_sequence(request, complexTypeChild, xml_tree, full_path=full_path,
                                             edit_data_tree=edit_data_tree, schema_location=schema_location)
        else:
            # does it contain choice ?
            complexTypeChild = element.find('{0}choice'.format(LXML_SCHEMA_NAMESPACE))
            if complexTypeChild is not None:
                form_string += generate_choice(request, complexTypeChild, xml_tree, full_path=full_path,
                                               edit_data_tree=edit_data_tree, schema_location=schema_location)
            else:
                form_string += ""

    return form_string
