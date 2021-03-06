#!/usr/bin/python

import argparse
import csv
import ast
import math
import sys

from os import listdir

def read_searches(file, id_to_pubs, all_unique_pubs):
    '''
    This function recieves a searches_by_year file and two dictionaries to which it adds identifiers taken from the searches_by_year file.
    '''
    path = 'searches_by_year/'+str(file)
    print(path)
    f = open(path, 'r')
    lines = f.readlines()

    for line in lines:
        if line == lines[0]: #skip header
            pass
        else:
            line = line.strip().split(',')
            publication = line[0].strip('\"')
            url = line[1]

            if url == '': # publication with no id
                pass
            else: # publications with ids
                id = url.split("_")[1].strip('\"')
                try:
                    id_to_pubs[id].add(publication) # check if id is already in dictionary, add to set of publications
                except:
                    id_to_pubs[id] = {publication}

            all_unique_pubs.add(publication) # seperate set for all unique publications (with our without ids)

    return id_to_pubs, all_unique_pubs

def make_table(data, id_to_tfidf, id_to_counts):
    '''
    This function recieves the data of all the ChEBI files in the files folder and the ids of the query search.
    It returns a dictionary of the query ids and their properties from the ChEBI files, if those properties are there.
    e.g. if there is no logP value, the id is not added to the dictionary that is returned.
    '''
    table = dict()
    failed = 0

    for id in id_to_counts.keys():
        try:
            if data["Mass"][id] != "-" and data["logP"][id] != "-":
                counts = id_to_counts[id]
                tfidf = id_to_tfidf[id]
                name = data["Names"][id]
                logP = data["logP"][id]
                mass = data["Mass"][id]
                superterms = data["Superterms"][id]
                table[id] = {"Count": counts, "tfidf": tfidf, "Names": name, "Mass": mass, "logP": logP, "Superterms": superterms}
            else:
                failed += 1
        except:
            failed += 1

    print('From %d of %d ChEBI IDs not all properties could be found' % (failed, len(id_to_counts.keys()) ))
    return table

def write_table(table, term): # header?
    '''
    This function writes the table in a .tsv file and names this file after the (shortest) query search term.
    '''
    file = "tables/"+str(term)+"_table.tsv"
    with open(file, 'w', newline='', encoding="utf-8") as tsvfile:
        writer = csv.writer(tsvfile, delimiter = '\t')
        # writer.writerow(header)
        for id in table.keys():
            row = [id]
            for col in table[id].keys(): # col juiste naam?
                row.append(table[id][col])
            writer.writerow(row)

def read_input(file):
    '''
    This functions reads the input file with query ids that were found in the search, makes a count for every id and puts this in a dictionary
    with the id as key and count as value.
    '''
    term = file.split('\\')[1].split('_')[0]
    f = open(file, 'r')
    input = f.readlines()
    id_to_publications = dict()
    id_to_counts = dict()
    for line in input:
        id = line.split()[0]
        publication = line.split()[1]

        try: # for every id, make a set of publications in which it appears
            id_to_publications[id].add(publication)
        except:
            id_to_publications[id] = set(publication)
        try: # for every id, count how many times it appears in all documents
            id_to_counts[id] += 1
        except:
            id_to_counts[id] = 1
    uniques = len(id_to_counts.keys())
    print('Input file contains %d unique ChEBI IDs' % uniques)
    return id_to_counts, id_to_publications, term

def read_file(file, key, data):
    '''
    This function reads a file and adds the information + id in a dictionary. This is added to another dictionary as value, and the term that describes the
    information (e.g. "Names") as key.
    '''
    f = open(file, 'r')
    lines = f.readlines()
    id_to_info = dict()
    for line in lines:
        line_to_list = line.split('\t')
        id = line_to_list[0]
        info = line_to_list[1].strip()
        id_to_info[id] = info

    data[key] = id_to_info

    return data

def normalization(id_to_counts, id_to_pubs, all_unique_pubs):
    '''
    This function performs the tfidf normalization ( see https://en.wikipedia.org/wiki/Tf%E2%80%93idf )
    '''
    N = len(all_unique_pubs)
    id_to_tfidf = dict()
    for id in id_to_counts.keys():
        tf = id_to_counts[id]
        try:
            npubs = len(id_to_pubs[id])
        except:
            npubs = 0

        idf = math.log(N/(1+npubs))
        tfidf = tf*idf
        id_to_tfidf[id] = math.floor(tfidf)

    return id_to_tfidf

def parser():
    parser = argparse.ArgumentParser(description='This script makes a table of the query IDs, their names and their properties')
    parser.add_argument('-i', required=True, metavar='input', dest='input', help='[i] to select input folder or input file from the results folder ')
    parser.add_argument('-t', required=True, metavar='type', dest='type', help='[t] to select type of input: file or folder')
    arguments = parser.parse_args()
    return arguments

def main():
    args = parser()
    input_type = args.type
    input = args.input
    if input_type == 'file':
        results = [input]
    elif input_type == 'folder':
        files = listdir('results')
        results = []
        for file in files:
            result = 'results\\'+str(file)
            results.append(result)
    else:
        sys.exit('Error: please give \'file\' or \'folder\' as input type')

    # get the counts and unique publications for allt he chebi id's, plus the search term
    term_to_result = dict()
    for result in results:
        id_to_counts, id_to_publications, term = read_input(result)
        term_to_result[term] = {"counts": id_to_counts, "publications": id_to_publications}


    # get unique publications for all publications since 2005 (?)
    print('reading files for normalization...')
    searches_by_year = listdir('searches_by_year')
    all_ids_to_publication = dict()
    all_publications = set()
    for file in searches_by_year:
        if '.csv' in file:
            all_ids_to_publication, all_publications = read_searches(file, all_ids_to_publication, all_publications)

    # normalization
    print('perform normalization...')
    for term in term_to_result.keys():
        id_to_counts = term_to_result[term]['counts']
        id_to_tfidf = normalization(id_to_counts, all_ids_to_publication, all_publications)
        term_to_result[term]['tfidf'] = id_to_tfidf

    # get properties for the chebi ids from the chebi files
    print('reading files with properties...')
    files = ['files/ChEBI2Names.tsv', 'files/ChEBI2Mass.tsv', 'files/ChEBI2logP.tsv', 'files/ChEBI2Superterms.tsv']
    data = dict()
    for file in files:
        key = file.split('2')[1].split('.')[0]
        data = read_file(file, key, data)

    # make table with chebi ids found in the search (all chebi ids in id_to_counts) plus their normalized counts (id_to_tfidf) and all properties (data)
    print('making the table...')
    for term in term_to_result.keys():
        id_to_tfidf = term_to_result[term]['tfidf']
        id_to_counts = term_to_result[term]['counts']
        table = make_table(data, id_to_tfidf, id_to_counts)
        write_table(table, term)

if __name__ == '__main__':
    main()
