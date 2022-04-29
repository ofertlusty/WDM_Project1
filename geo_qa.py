import sys
import requests 
import lxml.html 
import rdflib

# TODO: Main problems: 
# Retrival: 
#   1) [ ] - Gibrish URL that cause gibrish names (none standart letters) - TODO: Ofer -  Use encoding utf-8 and parse using urlib.parse.quete? [https://moodle.tau.ac.il/mod/forum/discuss.php?d=92883]
#       a) Countries: /wiki/s%c3%a3o_tom%c3%a9_and_pr%c3%adncipe (São Tomé and Príncipe - 187), /wiki/cura%c3%a7ao (Curaçao (Netherlands) - 192)
#       b) Names: andr%c3%a9s_manuel_l%c3%b3pez_obrador
#       c) Capitals: "bras%c3%adlia" -> should be Brasília
#   2) [ ] - Countries list: Missing 3 countries (Western_Sahara 170, Channel_Islands 190, Afghanistan 37)
#   3) Population: 
#       a) [ ] - Set standart with "," and not "."
#       b) [ ] - Take the first population found in infobox [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96655]
#   4) Date of birth: 
#       a) [ ] - Set standart as "1966-04-28" and not "28_april_1966" - use dateutil package?
#       b) [ ] - The date of birth will be taken from the "bday" row, if not exist we ignore it [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96463]
#   5) [ ] - Area: Set standart as "923,769 km squared" with miles and not as "148,460" (bangladesh), "3,796,742 sq mi_(9,833,520 km" (united states) [https://moodle.tau.ac.il/mod/forum/discuss.php?d=93424]
#   6) [ ] - Goverment: Fix query so we won't get cite notes like "#cite_note-bækken2018-7"
#   7) [ ] - Countries/Capitals: Dictionary for countries and capitals with several names (US, U.S, United states, Washngton, Washingon D.C...)
#   8) [ ] - Capital: philippines has 2 capitals: "manila" and "metro_manila" - which one to choose? 
#   9) Place of birth:
#       [ ] - a) create a set of countries from source URL and compare the place of birth to this set, if not there, keep empty [https://moodle.tau.ac.il/mod/forum/discuss.php?d=97142]
#       [ ] - b) TODO: Do we need to expand US, USA to united states? wait for answer [https://moodle.tau.ac.il/mod/forum/discuss.php?d=99213]
#   10) [ ] - Multiple result - sortlaksi and divided by "," [https://moodle.tau.ac.il/mod/forum/discuss.php?d=95427]
#   11) [ ] - empty result in query (no prime minister) won't be tested, and we can choose what to return [https://moodle.tau.ac.il/mod/forum/discuss.php?d=96099]
#       TODO: Tom - for now I ignore it, we you want to set somthing otherwise for debug let me know :)
#   12) [ ] - If data is not in info box itdoesn't exist & We look for the spesific relation like "President" and not "President of the SAC" (north korea) [https://moodle.tau.ac.il/mod/forum/discuss.php?d=95890]
#   13) [ ] - packeges - can be use with "BeautifulSoup" and "dateutil" if needed
#   14) [ ] - TODO: Format of result wair for answer [https://moodle.tau.ac.il/mod/forum/discuss.php?d=99213]

# ---------------------------------------- CONSTANTS ----------------------------------------
CREATE_ARGV           = "create"
QUESTION_ARGV         = "question"
SOURCE_URL            = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
WIKI_PREFIX           = "https://en.wikipedia.org"
ONTOLOGY_FILE_NAME    = "ontology.nt"

# ---------------------------------------- XPATH Queries ----------------------------------------
# TODO: Tom - ontology entities will be used all lower case with "_" as spaces, at the final result we need to set it back to "normal"
# TODO: Tom - if query is empty I ignore it for now 

XPATH_QUERY_COUNTRY_URL_WITH_SPAN         = '//table[1]//tr/td[1]/span[1]/a/@href'
# Another option: XPATH_QUERY_COUNTRY_URL_WITHOUT_SPAN      = '//table[1]//tr/td[1]/a/@href'

XPATH_QUERY_COUNTRY_TO_PRESIDENT          = '//table[contains(@class, "infobox")]//tr//a[text()="President"]/ancestor::tr/td//a[1]/@href'
XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER     = '//table[contains(@class, "infobox")]//tr//a[text()="Prime Minister"]/ancestor::tr/td//a[1]/@href'
XPATH_QUERY_COUNTRY_TO_POPULATION         = '//table[contains(@class, "infobox")]//tr//a[contains(text(), "Population")]/following::tr[1]/td/text()[1]'
XPATH_QUERY_COUNTRY_TO_AREA               = '//table[contains(@class, "infobox")]//tr//a[contains(text(), "Area")]/following::tr[1]/td/text()[1]'
XPATH_QUERY_COUNTRY_TO_GOVERMENT          = '//table[contains(@class, "infobox")]//tr//a[text()="Government"]/ancestor::tr/td//a/@href'
XPATH_QUERY_COUNTRY_TO_CAPITAL            = '//table[contains(@class, "infobox")]//tr/th[text()="Capital"]/ancestor::tr//td[1]/a//@href'
XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH       = '//table[contains(@class, "infobox")]//tr//th[text()="Born"]/parent::tr//span[@class="bday"]/text()'
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH    = '//table[contains(@class, "infobox")]//tr//th[text()="Born"]/parent::tr/td/text()[last()]' 

# ---------------------------------------- Ontology ----------------------------------------
# TODO: Tom - add prefix? 
ONTOLOGY_RELATION_PRESIDENT_OF            = "president_of"
ONTOLOGY_RELATION_PRIME_MINISTER_OF       = "prime_minister_of"
ONTOLOGY_RELATION_POPULATION_OF           = "population_of"
ONTOLOGY_RELATION_AREA_OF                 = "area_of"
ONTOLOGY_RELATION_GOVERMENT_IN            = "government_in"
ONTOLOGY_RELATION_CAPITAL_OF              = "capital_of"
ONTOLOGY_RELATION_BORN_ON                 = "born_on"
ONTOLOGY_RELATION_BORN_IN                 = "born_in"

ONTOLOGY_RELATION_PERSON_LST              = [ONTOLOGY_RELATION_PRESIDENT_OF, ONTOLOGY_RELATION_PRIME_MINISTER_OF]

# ---------------------------------------- Global ----------------------------------------
visited = set()

def cleanName(name):
    return name.strip().lower().replace(" ","_")

def addTupleToGraph(graph, entity1, relation, entity2):
        # TODO: Tom - add prefix? 
        ontologyEntity1 = rdflib.URIRef(entity1)
        ontologyRelation = rdflib.URIRef(relation)
        ontologyEntity2 = rdflib.URIRef(entity2)
        graph.add( (ontologyEntity1, ontologyRelation, ontologyEntity2) )
        
        # TODO: debug
        # print(f"ontologyEntity1(Country\Person): \t{ontologyEntity1}") 
        # print(f"ontologyRelation: \t{ontologyRelation}") 
        # print(f"ontologyQueryResult: \t{ontologyEntity2}") 

def InsertPersonEntity(graph, doc, personName, query, relation):
    # TODO: debug
    # print("\n#################### InsertPersonEntity ####################\n")
    # print(f"personName: {personName}\t query: {query}\t relation: {relation}")

    queryResults = doc.xpath(query) 
    for resultUrl in queryResults: 
        resultName = cleanName(resultUrl.split("/")[-1])
        addTupleToGraph(graph, personName, relation, resultName)

def InsertCountryEntity(graph, doc, countryName, query, relation):
    # TODO: debug 
    # print("\n#################### InsertCountryEntity ####################\n")
    # print(f"countryName: {countryName}\t  query: {query}\t relation: {relation}")

    queryResults = doc.xpath(query) 
    for resultUrl in queryResults:
        resultName = cleanName(resultUrl.split("/")[-1])
        addTupleToGraph(graph, resultName, relation, countryName)

        if relation in ONTOLOGY_RELATION_PERSON_LST:
            if resultUrl in visited:
                continue
            
            # TODO: debug 
            # print(f"URL: {WIKI_PREFIX}{resultUrl}")
            result = requests.get(f"{WIKI_PREFIX}{resultUrl}")
            doc = lxml.html.fromstring(result.content)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH, ONTOLOGY_RELATION_BORN_ON)
            InsertPersonEntity(graph, doc, resultName, XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH, ONTOLOGY_RELATION_BORN_IN)    
            
            # Finish working on countryUrl
            visited.add(resultUrl)

def addOntologyEntity(graph, countryUrl):
    # Check if Url has been searched, if not add to set and search it, else return. 
    if countryUrl in visited:
        return
    
    result = requests.get(countryUrl)
    doc = lxml.html.fromstring(result.content)
    countryName = cleanName(countryUrl.split("/")[-1])

    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRESIDENT, ONTOLOGY_RELATION_PRESIDENT_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER, ONTOLOGY_RELATION_PRIME_MINISTER_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_POPULATION, ONTOLOGY_RELATION_POPULATION_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_AREA, ONTOLOGY_RELATION_AREA_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_GOVERMENT, ONTOLOGY_RELATION_GOVERMENT_IN)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_CAPITAL, ONTOLOGY_RELATION_CAPITAL_OF)

    # Finish working on countryUrl
    visited.add(countryUrl)


def getCountriesUrl(): 
    result = requests.get(SOURCE_URL)
    doc = lxml.html.fromstring(result.content)
    countryRelUrl = doc.xpath(f"{XPATH_QUERY_COUNTRY_URL_WITH_SPAN}") 
    # countryRelUrl = doc.xpath(f"{XPATH_QUERY_COUNTRY_URL_WITH_SPAN | XPATH_QUERY_COUNTRY_URL_WITHOUT_SPAN}") # TODO: a lot of duplicated (US, UK, France, China when in () after the country)
    # country_url example ["https://en.wikipedia.org/wiki/Jordan", ... ]

    countryUrlLst = list()
    for countryUrl in countryRelUrl:
        countryUrlClean = cleanName(f"{WIKI_PREFIX}{countryUrl}")
        countryUrlLst.append(countryUrlClean)
    return countryUrlLst

def createOntology():
    graph = rdflib.Graph()
    countryUrlLst = getCountriesUrl()
    for countryUrl in countryUrlLst:
        addOntologyEntity(graph, countryUrl)
    graph.serialize(ONTOLOGY_FILE_NAME, format="nt")

def answerQuestion(question):
    # TODO: Tom's implementation 
    a = ""

if __name__ == '__main__':
    if ( sys.argv[1] == f"{CREATE_ARGV}" ):
        createOntology() 
    elif ( sys.argv[1] == f"{QUESTION_ARGV}" ):
        answerQuestion(sys.argv[2])
