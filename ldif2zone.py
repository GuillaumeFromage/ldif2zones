#!/usr/bin/python

import sys
from string import Template
from dns import *
from time import localtime, strftime, time
from easyzone import easyzone
from ldif import LDIFParser,LDIFWriter
import argparse

class MyLDIF(LDIFParser):
   def __init__(self,input,output,root,ns1,ns2,outputdir='.'):
      LDIFParser.__init__(self,input)
      self.writer = LDIFWriter(output)
      self.megaArray = {}
      self.valueInEntries = []
      self.megaTree = {}
      self.root = root
      self.ns1 = ns1
      self.ns2 = ns2
      self.zoneSubDirectory = outputdir
      self.megaWeirdArray= {}
      self.zoneArray = {}
      self.zoneArray = {}
      self.managedZones = {}
      self.exempted = {2: ['co.uk', 'org.ua', 'com.ar']}
   
   def initzone(self, textdomain):
       return {'ttl': '24H', 
           'subz': '',
           'main': '',
           'domain': textdomain,
           'serial': int(strftime('%Y%m%d00', localtime(time()))),
           'origin': textdomain + '.'}

   def zoneWrite(self, zone):
       if self.zoneArray.has_key(zone):
           zoneObj = self.zoneArray[zone]
           subst = dict(ttl=zoneObj['ttl'],
               serial=zoneObj['serial'],
               main=zoneObj['main'],
               ns1=self.ns1,
               ns2=self.ns2,
               subz=zoneObj['subz'],
               domain=zoneObj['domain'],
               origin=zoneObj['origin'])
           template = open('template.com', 'r')
           finalFile = open(self.zoneSubDirectory + '/' + zone, 'w')
           while 1: 
               modified = template.readline()
               if not modified: break
               hard = Template(modified).substitute(subst)
               finalFile.write(hard)
       else:
           exit("this zone doesn't exist");

   def printItOut(self):
       for a in self.managedZones:
           self.zoneWrite(a)

   def skimValuables(self, valuez):
       output = {}
       for a in ['aRecord','nSRecord','mXRecord','cNAMERecord']:
           if valuez.has_key(a):
               output[a] = valuez[a]
       return output
#       for a in values.keys():
#           if not self.valueInEntries.count(a):
#               print a
#               self.valueInEntries.append(a)

   def unfuckTemplating(self, domain, entry, value):
       remap = {'aRecord': 'A', 'nSRecord': 'NS', 'mXRecord': 'MX', 'cNAMERecord': 'CNAME'}
       # we'll just pad to 16 char
       return "" + domain.ljust(25) + remap[entry].ljust(7) + value + '\n'
 
   def insertSubZones(self, parent, values, textdomain_shrunk):
       valuables = self.skimValuables(values)
       for b in valuables:
           for c in values[b]:
               self.zoneArray[parent]['subz'] = self.zoneArray[parent]['subz'] + self.unfuckTemplating(textdomain_shrunk, b, c)


   def addrecords(self, zone, values, name):
       valuables = self.skimValuables(values)
       for b in valuables:
           for c in values[b]:
               self.zoneArray[name]['main'] = self.zoneArray[name]['main'] + self.unfuckTemplating('@', b, c)

        
   def recursiveDNCrap(self, DN='', tree='sentinel'):
       if DN=='':
          # okay this is a first run
          # we have the mega array sorted by depth, the shortest depth first so we can
          # start by the bottom
          if not tree=='sentinel':
              exit("this is broken, invoked dnscrap without a DN but with a tree")
          else:
              tree=self.megaTree
          for a in self.megaWeirdArray.keys():
              print a
              if a==1:
                  # we don't need zone file for those
                  print "skipping tlds"
              if a>=2:
		  # we need to create zone files for the fuckers
                  for b in self.megaWeirdArray[a].keys():
                      # we compute the domain name for the entry
                      domain=b.split(',')
                      domain.reverse() # again !
                      i = 0
		      dom_stripped = []
                      for c in domain:
                          # we just cut the dn= part of dn=fart
                          dom_stripped.append(c[3:])
                          i = i + 1
                      textdomain= ".".join(dom_stripped)
                      grandLevel = a
                      # we start at 1 less then the level we are. Eg: we're at fuck.shit.up, we go to shit.up
                      # normally, the first pass would always go
                      found = 0
                      print textdomain
                      while grandLevel >= 2:
                          parent = '.'.join(dom_stripped[-grandLevel:])
                          print parent + " grandLevel= " + str(grandLevel)
                          if self.managedZones.has_key(parent):
                              # found a parent domain
                              found = 1
                              self.insertSubZones(parent, self.megaWeirdArray[a][b], '.'.join(dom_stripped[0:a-grandLevel]))
                          grandLevel = grandLevel - 1
                      if not found: 
                          #print b + ':' + textdomain
                          if self.exempted.has_key(a) and self.exempted[a].count(textdomain) != 0:
                               print 'exempt !'
                               # the domain is not hosted by us we just skip it
                          else:
                          #print self.megaWeirdArray[a][b]
                              self.managedZones[textdomain] = 1
                              self.zoneArray[textdomain] = self.initzone(textdomain) 
                              self.addrecords(self.zoneArray[textdomain], self.megaWeirdArray[a][b], textdomain)
                      # for each, we 
#          for a in self.megaWeirdArray.keys():
#              print "depth" + str(a)
#              print self.megaWeirdArray[a].keys()
      

   def handle(self,dn,entry):
      arr = dn.split(',')
      arr.reverse()
      for component in self.root:
          if (not (arr[0] == component)):
              warn("this was a fucked up dn" + arr)
          else:
              arr.remove(component)
      depth = len(arr)
      arr2 = ",".join(arr)
      if not arr2 == '':
          self.megaArray[arr2] = entry
          if not self.megaWeirdArray.has_key(depth):
              self.megaWeirdArray[depth] = {}
          self.megaWeirdArray[depth][arr2] = entry
          if not self.megaArray[arr2].has_key('depth'):
              self.megaArray[arr2]['depth'] = depth
          else: 
              exit ("duplicate naming...")
      else:
          print "major fuckup for " + dn

args = argparse.ArgumentParser(description='Process some ldif file, that would contain dc elements and ns records, into a set of zones files.')
args.add_argument('--base', help="The base of the ldapdns config, eg: dc=org,dc=example,ou=system,ou=data,ou=dns", required=True)
args.add_argument('--ns1', help="ns1 for the domains", required=True)
args.add_argument('--ns2', help="ns2 for the domains", required=True)
args.add_argument('--infile', help="The input ldif file", required=True)
args.add_argument('--outdir', help="The output dir (it must already exist)")
a = args.parse_args()

root = a.base.split(',')
parser = MyLDIF(open(a.infile, 'rb'), sys.stdout, root, outputdir=a.outdir, ns1=a.ns1, ns2=a.ns2)
parser.parse()
parser.recursiveDNCrap()
parser.printItOut()

