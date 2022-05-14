import sys
import requests
import lxml.html
import rdflib
from dateutil import parser
import urllib

# ---------------------------------------- CONSTANTS ----------------------------------------
CREATE_ARGV           = "create"
QUESTION_ARGV         = "question"
SOURCE_URL            = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
WIKI_PREFIX           = "https://en.wikipedia.org"
ONTOLOGY_PRIFIX       = "http://example.org/"
AREA_OF_KM_SQURED     = "_km_squared"
JOE_BIDEN_URL         = "/wiki/Joe_Biden"

ONTOLOGY_FILE_NAME    = "ontology.nt"
COUNTRY_TYPE          = "country"
URL_TYPE              = "url"

# ---------------------------------------- XPATH Queries ----------------------------------------
XPATH_QUERY_COUNTRY_URL                           = '//table[1]//tr/td[1]/span[1]/a/@href'
XPATH_QUERY_COUNTRY_URL_AFGANISTAN                = '//tr//td//a[@title="Afghanistan"]/@href'
XPATH_QUERY_COUNTRY_URL_WESTERN_SAHARA            = '//tr//td//a[@title="Western Sahara"]/@href'
XPATH_QUERY_COUNTRY_URL_CHANNEL_ISLAND            = '//tr//td//a[@title="Channel Islands"]/@href'

XPATH_QUERY_COUNTRY_TO_PRESIDENT                  = '//table[contains(@class, "infobox")][1]//tr//*[text()="President"]/ancestor::tr/td//a[contains(@href, "wiki")][1]/@href'
XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER             = '//table[contains(@class, "infobox")][1]//tr//*[text()="Prime Minister"]/ancestor::tr/td//a[contains(@href, "wiki")][1]/@href'
XPATH_QUERY_COUNTRY_TO_POPULATION                 = '//table[contains(@class, "infobox")][1]//tr//*[contains(text(), "Population")]/following::tr[1]/td[1]/text()[1]'
XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE1         = '//table[contains(@class, "infobox")][1]//tr//*[text() = "Population"]/following::tr[1]/td//span/text()' # add query for channel islands / cook islands? 
XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE2         = '//table[contains(@class, "infobox")][1]//tr//*[text() = "Population"]/following::tr[1]/td//li[1]//text()'
XPATH_QUERY_COUNTRY_TO_AREA                       = '//table[contains(@class, "infobox")][1]//tr//*[contains(text(), "Area")]/following::tr[1]/td/text()[1]'
XPATH_QUERY_COUNTRY_TO_GOVERMENT                  = '//table[contains(@class, "infobox")][1]//tr//*[text()="Government"]/ancestor::tr/td//a[contains(@href, "wiki")]/@href'
XPATH_QUERY_COUNTRY_TO_CAPITAL                    = '//table[contains(@class, "infobox")][1]//*[text()="Capital"]/ancestor::tr//td[1]/a[contains(@href, "wiki")][1]//@href'
XPATH_QUERY_COUNTRY_TO_CAPITAL_ESWATINI           = '//table[contains(@class, "infobox")][1]//*[text()="Capital"]/ancestor::tr/td[1]//li[1]/a/@href'
XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH               = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr//span[@class="bday"]/text()'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT       = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr/td/text()[last()]'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT_FIGI  = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr/td//a[last()]/text()'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_A          = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr/td//a[contains(@href, "wiki")][last()]/@href' 

# ---------------------------------------- Ontology ----------------------------------------
ONTOLOGY_RELATION_PRESIDENT_OF                    = "president_of"
ONTOLOGY_RELATION_PRIME_MINISTER_OF               = "prime_minister_of"
ONTOLOGY_RELATION_POPULATION_OF                   = "population_of"
ONTOLOGY_RELATION_AREA_OF                         = "area_of"
ONTOLOGY_RELATION_GOVERMENT_IN                    = "government_in"
ONTOLOGY_RELATION_CAPITAL_OF                      = "capital_of"
ONTOLOGY_RELATION_BORN_ON                         = "born_on"
ONTOLOGY_RELATION_BORN_IN                         = "born_in"

ONTOLOGY_RELATION_PERSON_LST                      = [ONTOLOGY_RELATION_PRESIDENT_OF, ONTOLOGY_RELATION_PRIME_MINISTER_OF]

# ---------------------------------------- Global ----------------------------------------
countrySet = set()      # Set of all countries found in SOURCE URL (https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations))

# The function cleanName setteting the name according to the type's standart as describes below.
# List of types: URL, country or all kind of relations as shows at the macro list above under Ontology section. 
def cleanName(name, type):
    # Type: ONTOLOGY_RELATION_PERSON_LST
    # Person name taken from the URL - Needed to pars name with the following actions: 
    # 1) Parse as utf-8 for special letters
    # 2) Remove wiki prefix
    # 3) Strip and replace spaces as "_"
    if type in ONTOLOGY_RELATION_PERSON_LST: 
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.split("/")[-1].strip().replace(" ","_").replace('"', "")
            
    # Type: ONTOLOGY_RELATION_POPULATION_OF
    # 1) Split string using space delimiter for population contains additioanl data such as validity date (such as: '53,582,855 (2017)'
    # 3) Replacing dots (".") with commas (",") (such as: '273.879.750' -> '273,879,750')
    # 4) strip and replace spaces as "_"
    elif type == ONTOLOGY_RELATION_POPULATION_OF:
        result = name.strip().split(" ")[0].replace(" ","_").replace(".", ",")

    # Type: ONTOLOGY_RELATION_AREA_OF
    # 1) Split string using "km" delimiter for setting the standart result as a pure number, we add "km squred" at the final answer (such as: '53,582,855 (2017)'
    # 2) Strip
    # 3) Concatination of AREA_OF_KM_SQURED
    # 4) Spesicial cases: "United_States", "American_Samoa" - result writen in miles first, needed to split with "( and take the second part". (such as: '3,796,742 sq mi (9,833,520')
    elif type == ONTOLOGY_RELATION_AREA_OF: 
        result = name.split("km")[0].strip()
        result = f"{result}{AREA_OF_KM_SQURED}"

    # Type: ONTOLOGY_RELATION_GOVERMENT_IN
    # 1) Parse as utf-8 for special letters
    # 2) Strip and replace spaces as "_"
    # 3) Remove wiki prefix
    elif type == ONTOLOGY_RELATION_GOVERMENT_IN:
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.strip().replace(" ","_").split("/")[-1]

    # Type: ONTOLOGY_RELATION_CAPITAL_OF
    # 1) Parse as utf-8 for special letters
    # 2) Strip and replace spaces as "_"
    # 3) Remove wiki prefix
    elif type == ONTOLOGY_RELATION_CAPITAL_OF:
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.strip().replace(" ","_").split("/")[-1]

    # Type: ONTOLOGY_RELATION_CAPITAL_OF
    # 1) Parse as utf-8 for special letters
    # 2) Strip and replace spaces as "_"
    # 3) Remove wiki prefix and ")" when found (such as: 'Germany)')
    # 4) Split using delimiter "," to remove dates (such as: 'Republic_of_Egypt_(1953–1958)'), take first none-empty string

    elif type == ONTOLOGY_RELATION_BORN_IN:
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.split(",")
        if result[0] == "":
            result = result[1]
        else: 
            result = result[0]
        result = result.split("/")[-1].strip().replace(" ", "_").replace(")","")
    
    # Type: ONTOLOGY_RELATION_BORN_ON
    # 1) Strip and replace spaces as "_"
    # 2) Parsing date to set the standart of YYYY-MM-DD
    elif type == ONTOLOGY_RELATION_BORN_ON: 
        result = name.strip().replace(" ","_")
        result = parser.parse(result, yearfirst = True)
        
        day = 0 
        if (result.day < 10 ):
            day = f"0{result.day}"
        else: 
            day = result.day

        month = 0 
        if (result.month < 10 ):
            month = f"0{result.month}"
        else: 
            month = result.month

        result = f"{result.year}-{month}-{day}"
    
    # Type: COUNTRY_TYPE
    # 1) Parse as utf-8 for special letters
    # 2) Strip and replace spaces as "_"
    # 3) Remove wiki prefix
    elif type == COUNTRY_TYPE: 
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.split("/")[-1].strip().replace(" ","_")

    # Type: URL_TYPE
    # Parse as utf-8 for special letters
    elif type == URL_TYPE:
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")

    else: 
        print("ERROR: unsupported type for cleanName() function!")
        # Should not get here 
        return -1
        
    return result

# The function addTupleToGraph add the tupple of (entitya, relation, entity2) into graph while adding the wiki prefix. 
def addTupleToGraph(graph, entity1, relation, entity2):
        ontologyEntity1 = rdflib.URIRef(f"{ONTOLOGY_PRIFIX}{entity1}")
        ontologyRelation = rdflib.URIRef(f"{ONTOLOGY_PRIFIX}{relation}")
        ontologyEntity2 = rdflib.URIRef(f"{ONTOLOGY_PRIFIX}{entity2}")
        graph.add( (ontologyEntity1, ontologyRelation, ontologyEntity2) )


# The function InsertPersonEntity run the xpath query and adding the result to the graph. 
# While relation is ONTOLOGY_RELATION_BORN_IN the function checks if the country of the person was born in is found in the country list, 
# if not we throw the result and move to the next one. 
def InsertPersonEntity(graph, doc, personName, query, relation):
    queryResults = doc.xpath(query) 
    for resultUrl in queryResults: 
        resultName = cleanName(resultUrl, relation)        
        if ( (relation == ONTOLOGY_RELATION_BORN_IN) and (resultName not in countrySet)): 
            if (personName == "Wiliame_Katonivere"): 
                # The place of bitrh of the prime minister of Fiji is located in a unique location 
                queryResults2 = doc.xpath(XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT_FIGI)
            else: 
                queryResults2 = doc.xpath(XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT)
            
            for resultUrl2 in queryResults2:
                resultName2 = cleanName(resultUrl2, relation) 


                if ( resultName2 in countrySet ):                     
                    addTupleToGraph(graph, personName, relation, resultName2)
                else: 
                    return 

        else: 
            addTupleToGraph(graph, personName, relation, resultName)

# The function InsertCountryEntity run the xpath query and adding the result to the graph. 
# While relation is ONTOLOGY_RELATION_PERSON_LST the function get the URL content and run queries of Date\place of birth.
# While relation is ONTOLOGY_RELATION_CAPITAL_OF we add wiki prefix and encode with utf-8 for special charecters. 
# While relation is ONTOLOGY_RELATION_AREA_OF and countries are "United_States" or "American_Samoa" we want to take the size of the country in km squared found in parenthesis.
def InsertCountryEntity(graph, doc, countryName, query, relation):
    queryResults = doc.xpath(query)
    for resultUrl in queryResults:
        resultName = cleanName(resultUrl, relation)
        if relation in ONTOLOGY_RELATION_PERSON_LST:
            resultNameUTF8 = cleanName(f"{WIKI_PREFIX}{resultUrl}", URL_TYPE)
            resultName = cleanName(resultNameUTF8, relation)
            result = requests.get(f"{WIKI_PREFIX}{resultUrl}")
            doc = lxml.html.fromstring(result.content)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH, ONTOLOGY_RELATION_BORN_ON)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_A, ONTOLOGY_RELATION_BORN_IN)                
        elif ( relation == ONTOLOGY_RELATION_CAPITAL_OF ):
            resultName = cleanName(f"{WIKI_PREFIX}{resultUrl}", relation)
        elif ( ( relation == ONTOLOGY_RELATION_AREA_OF ) and ( countryName in ("United_States", "American_Samoa") ) ): 
            resultName = cleanName(resultUrl.split("(")[1], relation)
          
        addTupleToGraph(graph, resultName, relation, countryName)

# The function addOntologyEntity get the URL content, add the country to CountrySet and calls the fuctions resposible for creating the ontology. 
# Notice there special cases for some counties and relations that requeried us to create several queries for diffrenent relations.
def addOntologyEntity(graph, countryUrl):
    result = requests.get(countryUrl)
    doc = lxml.html.fromstring(result.content)
    countryName = cleanName(countryUrl, COUNTRY_TYPE)
    countrySet.add(countryName)

    # President
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRESIDENT, ONTOLOGY_RELATION_PRESIDENT_OF)
    
    # Prime minister
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER, ONTOLOGY_RELATION_PRIME_MINISTER_OF)
    
    # Population 
    if ( countryName in ("Belarus", "Malta", "Dominican_Republic")): 
        InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE1, ONTOLOGY_RELATION_POPULATION_OF)
    elif ( countryName  == "Russia" ):
        InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE2, ONTOLOGY_RELATION_POPULATION_OF)
    else: 
        InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_POPULATION, ONTOLOGY_RELATION_POPULATION_OF)
    
    # Area
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_AREA, ONTOLOGY_RELATION_AREA_OF)
    
    # Goverment
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_GOVERMENT, ONTOLOGY_RELATION_GOVERMENT_IN)
    
    # Capital
    if (countryName == "Eswatini"):
        InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_CAPITAL_ESWATINI, ONTOLOGY_RELATION_CAPITAL_OF)
    else:
        InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_CAPITAL, ONTOLOGY_RELATION_CAPITAL_OF)

# The function getCountriesUrl get all counties URL from SOURCE_URL. Notice that 3 of the countries wasn't found with the general query and therefore we added a special queries for them. 
def getCountriesUrl():
    result = requests.get(SOURCE_URL)
    doc = lxml.html.fromstring(result.content)
    countryRelUrl = doc.xpath(f"{XPATH_QUERY_COUNTRY_URL} | {XPATH_QUERY_COUNTRY_URL_AFGANISTAN} | {XPATH_QUERY_COUNTRY_URL_WESTERN_SAHARA} | {XPATH_QUERY_COUNTRY_URL_CHANNEL_ISLAND}") 
    # country_url example ["https://en.wikipedia.org/wiki/Jordan", ... ]

    countryUrlLst = list()
    for countryUrl in countryRelUrl:
        countryUrlClean = cleanName(f"{WIKI_PREFIX}{countryUrl}", URL_TYPE)
        countryUrlLst.append(countryUrlClean)
    return countryUrlLst

# The function createOntology create the ontology for the graph and save it to the file ONTOLOGY_FILE_NAME
def createOntology():
    graph = rdflib.Graph()
    countryUrlLst = getCountriesUrl()
    for countryUrl in countryUrlLst:
        addOntologyEntity(graph, countryUrl)
    graph.serialize(ONTOLOGY_FILE_NAME, format="nt", encoding="utf-8", errors="ignore")


def whenWhereQuestion(parsed_question, g):
    place = '<' + ONTOLOGY_PRIFIX + 'born_in>'
    time = '<' + ONTOLOGY_PRIFIX + 'born_on>'
    pres = '<' + ONTOLOGY_PRIFIX + 'president_of>'
    prim = '<' + ONTOLOGY_PRIFIX + 'prime_minister_of>'
    isPresident = parsed_question[3] == 'president'
    countryBegin = 5 if isPresident else 6
    relationOfQuestion = place if parsed_question[0] == 'Where' else time
    titleOfQuestion = pres if isPresident else prim
    country = '<' + ONTOLOGY_PRIFIX + '_'.join(parsed_question[countryBegin:-1]) + '>'
    question = "select ?result where { ?person " + titleOfQuestion + country + " . ?person " + relationOfQuestion + " ?result.}"
    x = g.query(question)
    answers = [str(res.result).split("/")[-1] for res in x]
    answers.sort()
    print(", ".join(answers).replace("_", " "))


def listAllQuestion(parsed_question, g):
    # TODO: simple implementation, need to verify base assumptions
    if ' '.join(parsed_question[:7]) == 'countries whose capital name contains the string':
        sub_string = ' '.join(parsed_question[7:]).lower()
        question = "select ?country where { ?capital <http://example.org/capital_of> ?country filter contains(lcase(str(?capital)), '" +sub_string+ "') .}"
        answers = [str(res.country).split("/")[-1] for res in g.query(question)]
        answers.sort()
        print(", ".join(answers).replace("_", " "))


def whoIsQuestion(parsed_question, g):
    if parsed_question[0] == 'the':     # question is about a specific country
        country = '<' + ONTOLOGY_PRIFIX
        relationOfQuestion = '<' + ONTOLOGY_PRIFIX
        if parsed_question[1] == 'president':
            country += '_'.join(parsed_question[3:]) + '>'
            relationOfQuestion += 'president_of>'
        elif parsed_question[1] == 'prime' and parsed_question[2] == 'minister':
            country += '_'.join(parsed_question[4:]) + '>'
            relationOfQuestion += 'prime_minister_of>'
        question = "select ?result where { ?result " + relationOfQuestion + " " + country + " .}"
        x = g.query(question)
        answers = [str(res.result).split("/")[-1] for res in x]
        answers.sort()
        print(", ".join(answers).replace("_", " "))

    else:                               # question is about a specific person
        name = '<' + ONTOLOGY_PRIFIX + '_'.join(parsed_question) + '>'
        question = "select ?country where { " + name + " <http://example.org/president_of> ?country .}"
        pres_countries = g.query(question)
        pres_countries = ["President of " + str(res.country).split("/")[-1] for res in pres_countries]
        pres_countries.sort()
        question = "select ?country where { " + name + " <http://example.org/prime_minister_of> ?country .}"
        prim_countries = g.query(question)
        prim_countries = ["Prime Minister of " + str(res.country).split("/")[-1] for res in prim_countries]
        prim_countries.sort()
        answers = pres_countries + prim_countries
        print(", ".join(answers).replace("_", " "))


def whatIsQuestion(parsed_question, g):
    relationOfQuestion = '<' + ONTOLOGY_PRIFIX
    country = '<' + ONTOLOGY_PRIFIX
    if parsed_question[1] != "of":
        print("Unknown format of \'what is the\' type of question.")
        exit()                      # TODO: need to check of we end execution in this case.
    elif parsed_question[0] == 'capital':
        relationOfQuestion += 'capital_of>'
    elif parsed_question[0] == 'area':
        relationOfQuestion += 'area_of>'
    elif parsed_question[0] == 'population':
        relationOfQuestion += 'population_of>'
    elif parsed_question[0] == 'form' and parsed_question[2] == 'government' and parsed_question[3] == 'in':
        relationOfQuestion += 'government_in>'
        parsed_question = parsed_question[2:]       # remove 'form of'
    else:
        print("Unknown format of \'what is the\' type of question.")
        exit()                      # TODO: need to check of we end execution in this case.
    parsed_question = parsed_question[2:]           # remove the relation's words
    country += "_".join(parsed_question) + ">"
    question = "select ?result where { ?result "+relationOfQuestion+" "+country+" .}"
    outputWhatAnswer(g.query(question))
    return question

def outputWhatAnswer(x):
    tmp = list(x)
    answers = [str(res.result).split("/")[-1] for res in x]
    answers.sort()
    print(", ".join(answers).replace("_", " "))


def howManyQuestion(parsed_question, g):
    # TODO: question 25 has double space, need to check if it's on purpose
    if parsed_question[0] == 'presidents':
        country = '<' + ONTOLOGY_PRIFIX + '_'.join(parsed_question[4:]) + '>'
        question = 'select ?president (count(distinct ?president) as ?number) where {' \
                   ' ?president <http://example.org/president_of> ?country .'\
                   ' ?president <http://example.org/born_in> ' + country + ' }'
    else:
        i = parsed_question.index('are')
        government_form1 = '<' + ONTOLOGY_PRIFIX + '_'.join(parsed_question[:i]) + '>'
        government_form2 = '<' + ONTOLOGY_PRIFIX + '_'.join(parsed_question[i+2:]) + '>'
        question = 'select ?country (count(distinct ?country) as ?number) where {' \
                   + government_form1 + '<http://example.org/government_in> ?country .' \
                   + government_form2 + '<http://example.org/government_in> ?country .}'
    answer = [str(res.number).split("/")[-1] for res in g.query(question)]
    answer.sort()
    print(", ".join(answer))


def answerQuestion(question):
    g = rdflib.Graph()
    g.parse("ontology.nt", format="nt")
    question = question[:-1] if question[-1] == '?' else question
    parsed_question = question.split(" ")      # parse to list and remove '?'
    if parsed_question[0] == 'What':
        whatIsQuestion(parsed_question[3:], g)             # get rid of 'what is the'
    elif ' '.join(parsed_question[:2]) == 'Who is':
        whoIsQuestion(parsed_question[2:], g)              # get rid of 'who is'
    elif ' '.join(parsed_question[:2]) == 'List all':
        listAllQuestion(parsed_question[2:], g)
    elif ' '.join(parsed_question[:3]) == 'When was the' or ' '.join(parsed_question[:3]) == 'Where was the':
        whenWhereQuestion(parsed_question, g)
    elif ' '.join(parsed_question[:2]) == 'How many':
        howManyQuestion(parsed_question[2:], g)


if __name__ == '__main__':
    if ( sys.argv[1] == f"{CREATE_ARGV}" ):
        createOntology()
    elif ( sys.argv[1] == f"{QUESTION_ARGV}" ):
        answerQuestion(sys.argv[2])
