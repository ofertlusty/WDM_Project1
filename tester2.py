import rdflib
import subprocess
import os
"""g = rdflib.Graph()
g.parse("ontology.nt", format="nt")
#q = 'select ?capital where { ?capital <http://example.org/capital_of> ?country filter contains(?capital, \'hi\') .}'
q = 'select ?country where { ?p <http://example.org/president_of> ?country filter contains(str(?p), \'celo\').}'
tmp = g.query(q)
#tmp1 = g.query(q1)
x = list(tmp)
#x1 = list(tmp1)
answer = [str(res.country).split("/")[-1] for res in x]
answer.sort()
print(", ".join(answer))"""

file1 = open('test_questions.txt', 'r')
questions = file1.readlines()
for question in questions:
    print(f"Question: {question}", end="")
    cmd = "python ./geo_qa.py question"
    cmd += ' "' + question + '"'
    p = os.system(cmd)
    print(f"Status: {p}\n")