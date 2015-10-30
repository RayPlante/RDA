from models import CSVExporter
import unittest

class Test(unittest.TestCase):
    def setUp(self):
        print "In method", self._testMethodName


    def test_one_file(self):
        #The list of data
        dataXML = []
        #Instanciate the exporter
        exporter = CSVExporter()
        #Open the XML File
        xml = open('testData/example-2.xml','r')
        contentXml = xml.read()
        #Add the xml content to the list of data to transform
        dataXML.append({'title':'Results.csv', 'content': str(contentXml)})

        #Transformation
        contentRes = exporter._transform(dataXML)

        #Open the expected res
        resExpectedTable1 = open('testData/csv_result_one_Table1.txt','r')
        contentResExpectedTable1 = resExpectedTable1.read()
        resExpectedTable2 = open('testData/csv_result_one_Table2.txt','r')
        contentResExpectedTable2 = resExpectedTable2.read()

        #Comparison
        self.assertEquals(contentRes[0]['title'], 'Results_Table1')
        self.assertEquals(contentRes[1]['title'], 'Results_Table2')
        #We don't take into account the first 2 lines cause of the current date
        self.assertEquals("\n".join(contentRes[0]['content'].splitlines()), "\n".join(contentResExpectedTable1.splitlines()))
        self.assertEquals("\n".join(contentRes[1]['content'].splitlines()), "\n".join(contentResExpectedTable2.splitlines()))


    # def test_many_files(self):
    #     #The list of data
    #     dataXML = []
    #     #Instanciate the exporter
    #     exporter = POPExporter()
    #     #Open the XML File
    #     contentXml = open('testData/result1.xml','r').read()
    #     contentXml2 = open('testData/result2.xml','r').read()
    #     contentXml3 = open('testData/result3.xml','r').read()
    #     #Add the xml content to the list of data to transform
    #     dataXML.append({'title':'Results.pop', 'content': str(contentXml)})
    #     dataXML.append({'title':'Results.pop', 'content': str(contentXml2)})
    #     dataXML.append({'title':'Results.pop', 'content': str(contentXml3)})
    #
    #     #Transformation
    #     contentRes = exporter._transform(dataXML)
    #
    #     #Open the expected res
    #     resExpected = open('testData/pop_result_many.txt','r')
    #     contentResExpected = resExpected.read()
    #
    #     #Comparison
    #     self.assertEquals(contentRes[0]['title'], 'Results.pop')
    #     #We don't take into account the first 2 lines cause of the current date
    #     self.assertEquals("\n".join(contentRes[0]['content'].splitlines()[2:]), "\n".join(contentResExpected.splitlines()[2:]))



if __name__ == '__main__':
    unittest.main()