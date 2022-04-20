import sys
import requests 
import lxml.html 
import rdflib

# ---------------------------------------- CONSTANTS ----------------------------------------
CREATE_ARGV           = "create"
QUESTION_ARGV         = "question"
SOURCE_URL            = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
WIKI_PREFIX           = "https://en.wikipedia.org"
ONTOLOGY_FILE_NAME    = "ontology.nt"

# ---------------------------------------- XPATH Queries ----------------------------------------
# TODO: Ofer - set or check all queeries 
XPATH_QUERY_COUNTRY_URL_WITH_SPAN         = '//table[1]//tr/td[1]/span[1]/a/@href'
XPATH_QUERY_COUNTRY_URL_WITHOUT_SPAN      = '//table[1]//tr/td[1]/a/@href'
XPATH_QUERY_COUNTRY_TO_PRESIDENT          = '//table[contains(@class, "infobox")]/'
XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER     = '//table[contains(@class, "infobox")]//tr//a[text()="President"]//text()'
XPATH_QUERY_COUNTRY_TO_POPULATION         = ''
XPATH_QUERY_COUNTRY_TO_AREA               = ''
XPATH_QUERY_COUNTRY_TO_GOVERMENT          = '//table[contains(@class, "infobox")]//tr[th//text() = "Government"]/td//@title'
XPATH_QUERY_COUNTRY_TO_CAPITAL            = '//table[contains(@class, "infobox")]//tr[th//text() = "Capital"]//a/text()'
XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH       = ''
XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH    = ''

# ---------------------------------------- Ontology ----------------------------------------
# TODO: Tom - add prefix? 
ONTOLOGY_RELATION_PRESIDENT_OF            = "president_of"
ONTOLOGY_RELATION_PRIME_MINISTER_OF       = "prime_minister_of"
ONTOLOGY_RELATION_POPULATION_OF           = "population_of"
ONTOLOGY_RELATION_AREA_OF                 = "area_of"
ONTOLOGY_RELATION_GOVERMENT_IN            = "government_in"
ONTOLOGY_RELATION_CAPITAL_OF              = "capital_of"

# TODO: Ofer - Do we need to crawl like Dana with urls[] and visited? 

def getCountriesUrl(): 
    result = requests.get(SOURCE_URL)
    doc = lxml.html.fromstring(result.content)
    countryRelUrl = doc.xpath(f"{XPATH_QUERY_COUNTRY_URL_WITH_SPAN} | {XPATH_QUERY_COUNTRY_URL_WITHOUT_SPAN}")
    # country_url example ["https://en.wikipedia.org/wiki/Jordan", ... ]

    countrySet = set()
    for i in range(1, len(countryRelUrl)):
        countrySet.add(f"{WIKI_PREFIX}{countryRelUrl[i]}")
    
    countryUrlLst = list(countrySet)

    # TODO: OFer - found 236 countries - in wiki there are only 233
    # print(f"countryRelUrl len: {len(countryUrlLst)}")
    # for i in range(1, len(countryUrlLst)):
    #     print(f"{i} : {countryUrlLst[i]}")
    return countryUrlLst

def addOntologyEntity(graph, countryUrl):
    result = requests.get(countryUrl)
    doc = lxml.html.fromstring(result.content)
    countryName = countryUrl.split("/")[-1]
    print(f"in addOntologyEntity() \t countryName: {countryName}") # TODO: debug 
    
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRESIDENT, ONTOLOGY_RELATION_PRESIDENT_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_PRIME_MINISTER, ONTOLOGY_RELATION_PRIME_MINISTER_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_POPULATION, ONTOLOGY_RELATION_POPULATION_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_AREA, ONTOLOGY_RELATION_AREA_OF)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_GOVERMENT, ONTOLOGY_RELATION_GOVERMENT_IN)
    InsertCountryEntity(graph, doc, countryName, XPATH_QUERY_COUNTRY_TO_CAPITAL, ONTOLOGY_RELATION_CAPITAL_OF)
    

def InsertCountryEntity(graph, doc, countryName, query, relation):
    ontologtCountry = rdflib.URIRef(countryName)
    # TODO: Tom - add prefix? 
    # TODO: Ofer - implement function

    # if relation is ONTOLOGY_RELATION_PRESIDENT_OF or ONTOLOGY_RELATION_PRIME_MINISTER_OF add person entity
    # InsertPersonEntity(graph, doc, personName, XPATH_QUERY_PERSON_TO_DATE_OF_BIRTH, ONTOLOGY_RELATION_PRESIDENT_OF)
    # InsertPersonEntity(graph, doc, personName, XPATH_QUERY_PERSON_TO_COUNTRY_OF_BIRTH, ONTOLOGY_RELATION_PRESIDENT_OF)

def InsertPersonEntity(graph, doc, personName, query, relation):
    ontologtPerson = rdflib.URIRef(personName)
    # TODO: Ofer - implement function

def createOntology():
    graph = rdflib.Graph()
    countryUrlLst = getCountriesUrl()
    for i in range(1, len(countryUrlLst) + 1):
        print(f"{i} : {countryUrlLst[i]}") # TODO: debug 
        addOntologyEntity(graph, countryUrlLst)
    graph.serialize(ONTOLOGY_FILE_NAME, format="nt")

def answerQuestion(question):
    # TODO: Tom's implementation 
    a = ""

if __name__ == '__main__':
    if ( sys.argv[1] == f"{CREATE_ARGV}" ):
        createOntology() 
    elif ( sys.argv[1] == f"{QUESTION_ARGV}" ):
        answerQuestion(sys.argv[2])
