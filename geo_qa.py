from ast import parse
import sys
import requests
import lxml.html
import rdflib
from dateutil import parser
import urllib

# TODO: Main problems: 
# Retrival: 
#   1) [V] - Gibrish URL that cause gibrish names (none standart letters) [https://moodle.tau.ac.il/mod/forum/discuss.php?d=92883]
#       a) Countries: /wiki/s%c3%a3o_tom%c3%a9_and_pr%c3%adncipe (São Tomé and Príncipe - 187), /wiki/cura%c3%a7ao (Curaçao (Netherlands) - 192)
#       b) Names: andr%c3%a9s_manuel_l%c3%b3pez_obrador
#       c) Capitals: "bras%c3%adlia" -> should be Brasília
#   2) [V] - Countries list: Missing 3 countries (Western_Sahara 170, Channel_Islands 190, Afghanistan 37)
#   3) Population: 
#       a) [V] - Set standart with "," and not "."
#       b) [V] - Take the first population found in infobox [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96655]
#       c) [ ] - Wrong answers: cook_islands -> '17,459', %', 'males','age','females'
#   4) Date of birth: 
#       a) [V] - Set standart as "1966-04-28" and not "28_april_1966" - fix for 1966-01-28 and not 1966-1-28
#       b) [V] - The date of birth will be taken from the "bday" row, if not exist we ignore it [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96463]
#   5) [V] - Area: Set standart as "923,769 km squared"? and not as "148,460" (bangladesh), "3,796,742 sq mi_(9,833,520 km" (united states) [https://moodle.tau.ac.il/mod/forum/discuss.php?d=93424]
#   6) [V] - Goverment: Fix query so we won't get cite notes like "#cite_note-bækken2018-7"
#   7) [V] - Capital: philippines has 2 capitals: "manila" and "metro_manila" - which one to choose? The first one
#   8) Place of birth:
#       [V] - a) Create a set of countries from source URL and compare the place of birth to this set, if not there, keep empty [https://moodle.tau.ac.il/mod/forum/discuss.php?d=97142]
#       [V] - b) Do we need to expand US, USA to united states? No [https://moodle.tau.ac.il/mod/forum/discuss.php?d=99213]
#   9)  [V] - Multiple result - sort lacsi and divided by "," [https://moodle.tau.ac.il/mod/forum/discuss.php?d=95427]
#   10) [V] - Empty result in query (no prime minister) won't be tested, and we can choose what to return [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96099]
#       for now I ignore it, we you want to set somthing otherwise for debug let me know :)
#   11) [V] - If data is not in info box it doesn't exist & We look for the spesific relation like "President" and not "President of the SAC" (north korea) [https://moodle.tau.ac.il/mod/forum/discuss.php?d=95890]
#   12) [V] - packeges - can be use with "BeautifulSoup" and "datepip listutil" if needed
#   13) [V] - Format of result wait for answer [https://moodle.tau.ac.il/mod/forum/discuss.php?d=99213]
#   14) [ ] - TODO: waiting for response: name with qoutes - should we remove the qoutes? "http://example.org/Philip_"Brave"_Davis" [https://moodle.tau.ac.il/mod/forum/discuss.php?d=101393]

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
XPATH_QUERY_COUNTRY_URL                      = '//table[1]//tr/td[1]/span[1]/a/@href'
XPATH_QUERY_COUNTRY_URL_AFGANISTAN           = '//tr//td//a[@title="Afghanistan"]/@href'
XPATH_QUERY_COUNTRY_URL_WESTERN_SAHARA       = '//tr//td//a[@title="Western Sahara"]/@href'
XPATH_QUERY_COUNTRY_URL_CHANNEL_ISLAND       = '//tr//td//a[@title="Channel Islands"]/@href'

XPATH_QUERY_COUNTRY_TO_PRESIDENT             = '//table[contains(@class, "infobox")][1]//tr//*[text()="President"]/ancestor::tr/td//a[contains(@href, "wiki")][1]/@href'
XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER        = '//table[contains(@class, "infobox")][1]//tr//*[text()="Prime Minister"]/ancestor::tr/td//a[contains(@href, "wiki")][1]/@href'
XPATH_QUERY_COUNTRY_TO_POPULATION            = '//table[contains(@class, "infobox")][1]//tr//*[contains(text(), "Population")]/following::tr[1]/td[1]/text()[1]'
XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE1    = '//table[contains(@class, "infobox")][1]//tr//*[text() = "Population"]/following::tr[1]/td//span/text()' # add query for channel islands / cook islands? 
XPATH_QUERY_COUNTRY_TO_POPULATION_UNIQUE2    = '//table[contains(@class, "infobox")][1]//tr//*[text() = "Population"]/following::tr[1]/td//li[1]//text()'
XPATH_QUERY_COUNTRY_TO_AREA                  = '//table[contains(@class, "infobox")][1]//tr//*[contains(text(), "Area")]/following::tr[1]/td/text()[1]'
XPATH_QUERY_COUNTRY_TO_GOVERMENT             = '//table[contains(@class, "infobox")][1]//tr//*[text()="Government"]/ancestor::tr/td//a[contains(@href, "wiki")]/@href'
XPATH_QUERY_COUNTRY_TO_CAPITAL               = '//table[contains(@class, "infobox")][1]//*[text()="Capital"]/ancestor::tr//td[1]/a[contains(@href, "wiki")][1]//@href'
XPATH_QUERY_COUNTRY_TO_CAPITAL_ESWATINI      = '//table[contains(@class, "infobox")][1]//*[text()="Capital"]/ancestor::tr/td[1]//li[1]/a/@href'
XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH          = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr//span[@class="bday"]/text()'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT  = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr/td/text()[last()]'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_A     = '//table[contains(@class, "infobox")][1]//tr//*[text()="Born"]/parent::tr/td//a[contains(@href, "wiki")][last()]/@href' 

# ---------------------------------------- Ontology ----------------------------------------
ONTOLOGY_RELATION_PRESIDENT_OF               = "president_of"
ONTOLOGY_RELATION_PRIME_MINISTER_OF          = "prime_minister_of"
ONTOLOGY_RELATION_POPULATION_OF              = "population_of"
ONTOLOGY_RELATION_AREA_OF                    = "area_of"
ONTOLOGY_RELATION_GOVERMENT_IN               = "government_in"
ONTOLOGY_RELATION_CAPITAL_OF                 = "capital_of"
ONTOLOGY_RELATION_BORN_ON                    = "born_on"
ONTOLOGY_RELATION_BORN_IN                    = "born_in"

ONTOLOGY_RELATION_PERSON_LST              = [ONTOLOGY_RELATION_PRESIDENT_OF, ONTOLOGY_RELATION_PRIME_MINISTER_OF]
ONTOLOGY_RELATION_LOCATION_LST            = [ONTOLOGY_RELATION_CAPITAL_OF, ONTOLOGY_RELATION_BORN_IN]

# ---------------------------------------- Global ----------------------------------------
visited = set()         # Set of URLs we allready visited in
countrySet = set()      # Set of all countries found in SOURCE URL (https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations))

# The function cleanName setteting the name according to the type's standart as describes below.
# List of types: URL, country or all kind of relations as shows at the macro list above under Ontology section. 
def cleanName(name, type):
    # Type: ONTOLOGY_RELATION_PERSON_LST
    # Person name taken from the URL - Needed to pars name with the following actions: 
    # 1) Parse as utf-8 for special letters
    # 2) Remove wiki prefix
    # 3) Strip and replace spaces as "_"
    # 4) Removing '"' with none is necessery for some of the names to be serialized (such as: 'Philip_"Brave"_Davis')
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
    # 3) Split string usnig delimiter "-" for areas with range (such as: '20,770–22,072')
    # 4) Concatination of AREA_OF_KM_SQURED
    # 5) Spesicial cases: "United_States", "American_Samoa" - result writen in miles first, needed to split with "( and take the second part". (such as: '3,796,742 sq mi (9,833,520')
    elif type == ONTOLOGY_RELATION_AREA_OF: 
        result = name.split("km")[0].split("-")[0].strip()
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
    # 3) Remove wiki prefix
    # 4) Split using delimiter "," to remove dates (such as: 'Republic_of_Egypt_(1953–1958)'), take first none-empty string
    elif type == ONTOLOGY_RELATION_BORN_IN:
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        result = result.split(",")
        if result[0] == "":
            result = result[1]
        else: 
            result = result[0]
        result = result.split("/")[-1].strip().replace(" ", "_")
    
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
    # 4) Split using delimiter " " to remove dates (such as: 'Republic_of_Egypt_(1953–1958)'), take first none-empty string
    elif type == COUNTRY_TYPE: 
        result = urllib.parse.unquote(name, encoding="utf-8", errors="ignore")
        # result = result.split("/")[-1].strip().split(" ")[0].replace(" ","_")
        result = result.split("/")[-1].strip().replace(" ","_")

    # Type: URL_TYPE
    # 1) Parse as utf-8 for special letters
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
# While relation is ONTOLOGY_RELATION_BORN_IN the function checks if the country the person was born in is found in the country list, 
# if not we throw the result and move to the next one. 

# TODO: add description
def InsertPersonEntity(graph, doc, personName, query, relation):
    queryResults = doc.xpath(query) 
    for resultUrl in queryResults: 
        resultName = cleanName(resultUrl, relation)
        if ( (relation == ONTOLOGY_RELATION_BORN_IN) and (resultName not in countrySet)): 
            queryResults = doc.xpath(XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_TEXT)
            resultName = cleanName(resultUrl, relation)
            if ( resultName not in countrySet ): 
                # If the location isn't found at the countrySet (location is a city or a miss spell country other than those found at SOURCE URL)
                # than the result isn't valid [https://moodle.tau.ac.il/mod/forum/discuss.php?d=97142]
                return
        else: 
            addTupleToGraph(graph, personName, relation, resultName)

# TODO: add description
def InsertCountryEntity(graph, doc, countryName, query, relation):
    queryResults = doc.xpath(query)
    for resultUrl in queryResults:
        resultName = cleanName(resultUrl, relation)
        if relation in ONTOLOGY_RELATION_PERSON_LST:
            # if ( ( resultUrl in visited ) and ( resultUrl != JOE_BIDEN_URL) ):
            #     # TODO: OFer - Guam's president is also Joe Biden - should we skip the visited?? 
            #     continue
            
            resultNameUTF8 = cleanName(f"{WIKI_PREFIX}{resultUrl}", URL_TYPE)
            resultName = cleanName(resultNameUTF8, relation)
            result = requests.get(f"{WIKI_PREFIX}{resultUrl}")
            doc = lxml.html.fromstring(result.content)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH, ONTOLOGY_RELATION_BORN_ON)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH_A, ONTOLOGY_RELATION_BORN_IN)    
            
            # TODO: think about removing visited for person or both (persons and countries)
            # Finish working on countryUrl
            # visited.add(resultUrl)
        elif ( relation == ONTOLOGY_RELATION_CAPITAL_OF ):
            resultNameUTF8 = cleanName(f"{WIKI_PREFIX}{resultUrl}", URL_TYPE)
            resultName = cleanName(resultNameUTF8, relation)
        elif ( ( relation == ONTOLOGY_RELATION_AREA_OF ) and ( countryName in ("United_States", "American_Samoa") ) ): 
            resultName = cleanName(resultUrl.split("(")[1], relation)
          
        addTupleToGraph(graph, resultName, relation, countryName)

# TODO: add description
def addOntologyEntity(graph, countryUrl):
    # Check if Url has been searched, if not add to set and search it, else return. 
    if countryUrl in visited:
        return

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

    # Finish working on countryUrl
    visited.add(countryUrl)

# TODO: add description
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

# TODO: add description
def createOntology():
    graph = rdflib.Graph()
    countryUrlLst = getCountriesUrl()
    for countryUrl in countryUrlLst:
        addOntologyEntity(graph, countryUrl)
    graph.serialize(ONTOLOGY_FILE_NAME, format="nt", encoding="utf-8", errors="ignore")


def whenWhereQuestion(parsed_question, g):
    a = 0


def listAllQuestion(parsed_question, g):
    # TODO: simple implementation, need to verify base assumptions
    if ' '.join(parsed_question[:7]) == 'countries whose capital name contains the string':
        sub_string = ' '.join(parsed_question[7:])
        question = "select ?country where { ?capital <http://example.org/capital_of> ?country filter contains(str(?capital), '" +sub_string+ "') .}"
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
        relationOfQuestion += 'area_of>'         # TODO: add 'squared' at the end of answer
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
    # TODO: addressing capital letters
    tmp = list(x)
    answers = [str(res.result).split("/")[-1] for res in x]
    answers.sort()
    print(", ".join(answers).replace("_", " "))

def answerQuestion(question):
    g = rdflib.Graph()
    g.parse("ontology.nt", format="nt")
    question = question[:-1] if question[-1] == '?' else question
    parsed_question = question.lower().split(" ")      # parse to list and remove '?'
    if parsed_question[0] == 'what':
        whatIsQuestion(parsed_question[3:], g)             # get rid of 'what is the'
    elif parsed_question[0] == 'who' and parsed_question[1] == 'is':
        whoIsQuestion(parsed_question[2:], g)              # get rid of 'who is'
    elif parsed_question[0] == 'list' and parsed_question[1] == 'all':
        listAllQuestion(parsed_question[2:], g)
    elif ' '.join(parsed_question[:3]) == 'when was the' or ' '.join(parsed_question[:3]) == 'where was the':
        whenWhereQuestion(parsed_question[3:], g)


if __name__ == '__main__':
    if ( sys.argv[1] == f"{CREATE_ARGV}" ):
        createOntology()
    elif ( sys.argv[1] == f"{QUESTION_ARGV}" ):
        answerQuestion(sys.argv[2])
