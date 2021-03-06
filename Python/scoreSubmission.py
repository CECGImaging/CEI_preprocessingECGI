#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from __future__ import print_function

import argparse
import json
import os
import sys
import scipy.io
import zipfile

from selectMultipleSubmissions import *
from scoreCommon import evaluateL2



def extractZip(path, dest, flatten=True):
    """
    Extract a zip file, optionally flattening it into a single directory.
    """
    try:
        os.makedirs(dest)
    except OSError:
        if not os.path.exists(dest):
            raise

    try:
        with zipfile.ZipFile(path) as zf:
            if flatten:
                for name in zf.namelist():
                    # Ignore Mac OS X metadata
                    if name.startswith('__MACOSX'):
                        continue
                    outName = os.path.basename(name)
                    # Skip directories
                    if not outName:
                        continue
                    out = os.path.join(dest, outName)
                    with open(out, 'wb') as ofh:
                        with zf.open(name) as ifh:
                            while True:
                                buf = ifh.read(65536)
                                if buf:
                                    ofh.write(buf)
                                else:
                                    break
            else:
                zf.extractall(dest)
    except zipfile.BadZipfile as e:
        raise ScoreException('Could not read ZIP file "%s": %s' %
                             (os.path.basename(path), str(e)))


def unzipAll(directory, delete=True):

   # Unzip all zip files in directory and optionally delete them.
    #Return a list of the zip file names.

    zipFiles = [f for f in os.listdir(directory)
                if f.lower().endswith('.zip')]
    for zipFile in zipFiles:
        zipPath = os.path.join(directory, zipFile)
        #print ('This is zip path')
        #print (zipPath)
        extractZip(zipPath, directory)
        if delete:
            os.remove(zipPath)
    return zipFiles




def score(truthFile, testFile):

    scores = []

    metrics = [
        {
            'name': 'L2difference',
            'value': None
        },
        {
            'name':  'MFSsolution',
            'value': None
        }
    ]

    # load files
    truthMatrix = scipy.io.loadmat(truthFile)['Signal']['Ve'][0][0]
    testMatrix = scipy.io.loadmat(testFile)['Signal']['Ve'][0][0]

    # evaluate L2
    metrics[0]['value'] = evaluateL2( truthMatrix, testMatrix)

    print( metrics[0]['value']  )
    # evaluate MFS solution
#    metrics[1].value =

    scores.append({
        'dataset': os.path.basename(testFile),
        'metrics': metrics
    })

    return scores




def scoreAll(args):

    ## LOAD AND UNZIP TRUTH FILES
    # Unzip zip files contained in the input folders
    truthDir = args.groundtruth
    #print ('This is truth directory:')
    #print (truthDir)

    truthZipSubFiles = unzipAll(truthDir, delete=True)

    #print('With ZIP files:')
    #print (truthZipSubFiles)
    truthPath = None
    if truthZipSubFiles:
        truthPath = truthZipSubFiles[0]
    else:
        truthSubFiles = os.listdir(truthDir)
        if truthSubFiles:
            truthPath = truthSubFiles[0]
    #print('this is truthpath')
    #print(truthPath)
    if not truthPath:
        raise ScoreException(
            'Internal error: error reading ground truth folder: %s' % truthDir)


    # evaluate which files match each root
    truthMatches, rootNames = findFilesNameRoots(truthDir)
    
    ## LOAD AND UNZIP TEST DATA
    testDir = args.submission
    testZipSubFiles = unzipAll(testDir, delete=True)
    #print ('Unzip of both truth and test files successful!')
    testPath = None
    if testZipSubFiles:
        testPath = testZipSubFiles[0]
    else:
        testSubFiles = os.listdir(testDir)
        if testSubFiles:
            testPath = testSubFiles[0]
    #print('this is testpath')
    #print(testPath)
    if not testPath:
        raise ScoreException(
            'Internal error: error reading ground test folder: %s' % testDir)
   
    testMatches, test2TruthMatches = findFilesNameRoots2(testDir, truthMatches)
    
    # score each submission against every matching truth file
    scores = []
    for fi in range(len(testSubFiles)):
        for t2t in test2TruthMatches[fi]:
            #print('Scoring file ' + testSubFiles[fi] )
            #print('against file ' + truthSubFiles[t2t])
            scores.append( score( testDir + testSubFiles[fi], truthDir + truthSubFiles[t2t]))
    
    # if no scores raise an exception
    if scores==[]:
        raise ScoreException(
            'Internal error: There are no matching submission' )

    #print(scores)
    #print ('-------------------------Results are printed here-----------------------------')
    print(json.dumps(scores))
    #print ('-------------------------End of Results-----------------------------')

class ScoreException(Exception):
    pass

###  MAIN CODE
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Submission scoring helper script')
    parser.add_argument('-g', '--groundtruth', required=True,
                        help='path to the ground truth folder')
    parser.add_argument('-s', '--submission', required=True,
                        help='path to the submission folder')
    args = parser.parse_args()


    try:
        scoreAll(args)
    except ScoreException as e:
        covalicErrorPrefix = 'covalic.error: '
        print(covalicErrorPrefix + str(e), file=sys.stderr)
        exit(1)
