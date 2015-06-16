#!/usr/bin/env python

import argparse
import csv
from operator import itemgetter
import json
import os

# Constants
c_STR_INSPECTOR_TP = "TP"
c_STR_INSPECTOR_FP = "FP"
c_STR_INSPECTOR_FN = "FN"
c_STR_INSPECTOR_RNA_BAM = "RNA"
c_STR_INSPECTOR_DNA_BAM = "DNA"
c_STR_INSPECTOR_RNA_VCF = "RNA_VCF"
c_STR_INSPECTOR_DNA_VCF = "DNA_VCF"
c_I_NUMBER_RETURNED_CLASS_ERRORS = 10
c_STR_NO_CALL = "NA"
# Constants for tab files
c_I_TAB_DNA_LOCATION = 0
c_I_TAB_DNA_REF = 1
c_I_TAB_DNA_CALL = 2
c_I_TAB_DNA_COVERAGE = 3
c_I_TAB_RNA_LOCATION = 4
c_I_TAB_RNA_REF = 5
c_I_TAB_RNA_CALL = 6
c_I_TAB_RNA_COVERAGE = 7
c_I_TAB_RNA_STRAND = 8

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "make_inspector_json.py", description = "Creates the json object needed to view a RNA-Seq mutation validation comparison run.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "--input_files", required = True, dest = "lstr_input_files", action = "append", help = "A list of Sample name, RNA bam file, DNA bam file, RNA VCF file, DNA VCF file, tab file in a comma delimited string. Can be used more than once." )
prsr_arguments.add_argument( "--output_file", required = True, dest = "str_output_file", action = "store", help = "File to store the json object." )
args_call = prsr_arguments.parse_args()

# Object holding file info to become a json object for inspector visualization
# { sample : { RNA: file_path, DNA: file_path, FN: "Chr1-234 (145)": { "Chr": "1", "Loc": "234", "Cov": "145", "Ref": "A", "Alt": "T", "Strand": "+" }, FP: ..., TP: ...} }
dict_inspector = {}

# Go through each set of input files / info
for str_info in args_call.lstr_input_files:
  # Break up the input file string into file tokens
  str_sample_name, str_rna_bam, str_dna_bam, str_rna_vcf, str_dna_vcf, str_tab = str_info.split(",")

  # Check to make sure the files exist.
  for str_file in [ str_rna_bam, str_dna_bam, str_rna_vcf, str_dna_vcf, str_tab ]:
    if not os.path.exists( str_file ):
      print( "Error. The input file " + str_file + " does not exist. Skipping sample " + str_sample_name + "." )
      continue

  # Add sample and file names
  dict_sample = {}
  dict_sample[ c_STR_INSPECTOR_DNA_BAM ] = str_dna_bam
  dict_sample[ c_STR_INSPECTOR_RNA_BAM ] = str_rna_bam
  dict_sample[ c_STR_INSPECTOR_DNA_VCF ] = str_dna_vcf
  dict_sample[ c_STR_INSPECTOR_RNA_VCF ] = str_rna_vcf

  # Read in the VCF file
  llstr_tp = []
  llstr_fp = []
  llstr_fn = []
  # Open tab file
  with open( str_tab, "r" ) as  hndl_tab:
    csv_reader = csv.reader( hndl_tab, delimiter = "\t" )
    for lstr_tokens in csv_reader:
      # Skip the comments
      if lstr_tokens[0][0] == "#":
        continue

      # Change NA coverage to 0 coverage
      if lstr_tokens[ c_I_TAB_RNA_COVERAGE ].lower() == "na":
        lstr_tokens[ c_I_TAB_RNA_COVERAGE ] = 0
      if lstr_tokens[ c_I_TAB_DNA_COVERAGE ].lower() == "na":
        lstr_tokens[ c_I_TAB_DNA_COVERAGE ] = 0

      # Sort into error classes.
      STR_DNA_CALL = lstr_tokens[ c_I_TAB_DNA_CALL ]
      STR_RNA_CALL = lstr_tokens[ c_I_TAB_RNA_CALL ]

      if STR_DNA_CALL == c_STR_NO_CALL:
        # FP
        if not STR_RNA_CALL == c_STR_NO_CALL:
          llstr_fp.append( lstr_tokens )
      # FN
      elif STR_RNA_CALL == c_STR_NO_CALL:
        llstr_fn.append( lstr_tokens )
      # TP
      else:
        llstr_tp.append( lstr_tokens )

  # Get the top number of FP by coverage
  llstr_fp.sort( key=lambda x: int( x[ c_I_TAB_RNA_COVERAGE ] ), reverse=True )
  llstr_fp = llstr_fp[0:c_I_NUMBER_RETURNED_CLASS_ERRORS]
  # Get the top number of TP by coverage
  llstr_tp.sort( key=lambda x: int( x[ c_I_TAB_RNA_COVERAGE ] ), reverse=True )
  llstr_tp = llstr_tp[0:c_I_NUMBER_RETURNED_CLASS_ERRORS]
 
  # Get the top number of FN by coverage
  llstr_fn.sort( key=lambda x: int( x[ c_I_TAB_DNA_COVERAGE ] ), reverse=True )
  llstr_fn = llstr_fn[0:c_I_NUMBER_RETURNED_CLASS_ERRORS]
 
  # Add error class info
  # FP
  dict_fp = {}
  for lstr_fp in llstr_fp:
    lstr_alt = list( set( lstr_fp[ c_I_TAB_RNA_CALL ].split("/") ) )
    lstr_alt = [ str_base for str_base in lstr_alt if str_base not in [ lstr_fp[ c_I_TAB_RNA_REF ] ]]
    lstr_temp_chr_loc = lstr_fp[ c_I_TAB_RNA_LOCATION ].split( "--" )
    str_temp_chr = lstr_temp_chr_loc[ 0 ][ 3: ] if ( len( lstr_temp_chr_loc[ 0 ] ) > 3 ) and ( lstr_temp_chr_loc[0][ 0:3 ].lower() == "chr" ) else lstr_temp_chr_loc[ 0 ]
    str_temp_loc = lstr_temp_chr_loc[ 1 ]
    for str_alt_base in lstr_alt:
      dict_temp = { "Chr": str_temp_chr, "Loc": str_temp_loc,
                    "Cov": lstr_fp[ c_I_TAB_RNA_COVERAGE ], "Ref": lstr_fp[ c_I_TAB_RNA_REF ],
                    "Alt": str_alt_base, "Strand:": lstr_fp[ c_I_TAB_RNA_STRAND ] }
      dict_fp[ "-".join( [ "Chr"+str_temp_chr, str_temp_loc ] ) + " (" + lstr_fp[ c_I_TAB_RNA_COVERAGE ] + ")" ] = dict_temp
  dict_sample[ c_STR_INSPECTOR_FP ] = dict_fp
  # TP
  dict_tp = {}
  for lstr_tp in llstr_tp:
    lstr_alt = list( set( lstr_tp[ c_I_TAB_RNA_CALL ].split("/") ) )
    lstr_alt = [ str_base for str_base in lstr_alt if str_base not in [ lstr_tp[ c_I_TAB_RNA_REF ] ]]
    lstr_temp_chr_loc = lstr_tp[ c_I_TAB_RNA_LOCATION ].split( "--" )
    str_temp_chr = lstr_temp_chr_loc[ 0 ][ 3: ] if ( len( lstr_temp_chr_loc[ 0 ] ) > 3 ) and ( lstr_temp_chr_loc[0][ 0:3 ].lower() == "chr" ) else lstr_temp_chr_loc[ 0 ]
    str_temp_loc = lstr_temp_chr_loc[ 1 ]
    for str_alt_base in lstr_alt:
      dict_temp = { "Chr": str_temp_chr, "Loc": str_temp_loc,
                    "Cov": lstr_tp[ c_I_TAB_RNA_COVERAGE ], "Ref": lstr_tp[ c_I_TAB_RNA_REF ],
                    "Alt": str_alt_base, "Strand:": lstr_tp[ c_I_TAB_RNA_STRAND ] }
      dict_tp[ "-".join( [ "Chr"+str_temp_chr, str_temp_loc ] ) + " (" + lstr_tp[ c_I_TAB_RNA_COVERAGE ] + ")" ] = dict_temp
  dict_sample[ c_STR_INSPECTOR_TP ] = dict_tp
  # FN
  dict_fn = {}
  for lstr_fn in llstr_fn:
    lstr_alt = list( set( lstr_fn[ c_I_TAB_DNA_CALL ].split("/") ) )
    lstr_alt = [ str_base for str_base in lstr_alt if str_base not in [ lstr_tp[ c_I_TAB_DNA_REF ] ]]
    lstr_temp_chr_loc = lstr_fn[ c_I_TAB_DNA_LOCATION ].split( "--" )
    str_temp_chr = lstr_temp_chr_loc[ 0 ][ 3: ] if ( len( lstr_temp_chr_loc[ 0 ] ) > 3 ) and ( lstr_temp_chr_loc[0][ 0:3 ].lower() == "chr" ) else lstr_temp_chr_loc[ 0 ]
    str_temp_loc = lstr_temp_chr_loc[ 1 ]
    for str_alt_base in lstr_alt:
      dict_temp = { "Chr": str_temp_chr, "Loc": str_temp_loc,
                    "Cov": lstr_fn[ c_I_TAB_RNA_COVERAGE ], "Ref": lstr_fn[ c_I_TAB_RNA_REF ],
                    "Alt": str_alt_base, "Strand:": lstr_fn[ c_I_TAB_RNA_STRAND ] }
      dict_fn[ "-".join( [ "Chr"+str_temp_chr, str_temp_loc ] ) + " (" + lstr_fn[ c_I_TAB_RNA_COVERAGE ] + ")" ] = dict_temp
  dict_sample[ c_STR_INSPECTOR_FN ] = dict_fn
  dict_inspector[ str_sample_name ] = dict_sample

# Open handle and write json object to file
with open( args_call.str_output_file, "w" ) as hndl_output:
  hndl_output.write( json.dumps( dict_inspector, sort_keys=True, indent=2 ) )
