#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Adrien Vergé

"""familytreemaker

This program creates family tree graphs from simple text files.
"""

__author__ = "Adrien Vergé"
__copyright__ = "Copyright 2013, Adrien Vergé"
__license__ = "GPL"
__version__ = "1.1"

import argparse
import random
import re
import sys

class LayoutRuleEnforcer:
	"""Helper to enforce and verify layout rules for DOT output.
	Rules:
	- Spouse connections: Horizontal (East to West)
	- Child connections: Vertical (South to North)
	- Sibling bars: Horizontal (East to West)
	"""
	def __init__(self):
		self.total_edges = 0
		self.enforced_ports = 0

	def enforce(self, src, dst, edge_type):
		self.total_edges += 1
		s, d = src, dst
		
		if edge_type == 'spouse':
			if ':' not in s and not s.startswith('h'): s += ':e'
			if ':' not in d and not d.startswith('h'): d += ':w'
		elif edge_type == 'vertical':
			if ':' not in s: s += ':s'
			if ':' not in d: d += ':n'
		elif edge_type == 'horizontal':
			if ':' not in s: s += ':e'
			if ':' not in d: d += ':w'
		
		if s != src or d != dst:
			self.enforced_ports += 1
		
		return s, d

	def get_report(self):
		return "// Layout rules enforced: %d edges processed, %d ports corrected for alignment." % \
			(self.total_edges, self.enforced_ports)

class Person:
	def __init__(self, desc):
		self.attr = {}
		self.parents = []
		self.households = []

		desc = desc.strip()
		if '(' in desc and ')' in desc:
			self.name, attr = desc[0:-1].split('(')
			self.name = self.name.strip()
			attr = map(lambda x: x.strip(), attr.split(','))
			for a in attr:
				if '=' in a:
					k, v = a.split('=')
					self.attr[k] = v
				else:
					self.attr[a] = True
		else:
			self.name = desc

		if 'id' in self.attr:
			self.id = self.attr['id']
		else:
			self.id = re.sub('[^0-9A-Za-z]', '', self.name)
			if self.id == '' or 'unique' in self.attr:
				import hashlib
				self.id = 'P' + hashlib.md5(self.name.encode('utf-8')).hexdigest()

		self.follow_kids = True
		self.group = None # Group for vertical alignment

	def __str__(self):
		return self.name

	def graphviz(self):
		label = self.name
		if 'surname' in self.attr:
			label += '\\n« ' + str(self.attr['surname']) + '»'
		if 'birthday' in self.attr:
			label += '\\n' + str(self.attr['birthday'])
			if 'deathday' in self.attr:
				label += ' † ' + str(self.attr['deathday'])
		elif 'deathday' in self.attr:
			label += '\\n† ' + str(self.attr['deathday'])
		if 'notes' in self.attr:
			label += '\\n' + str(self.attr['notes'])
		opts = ['label="' + label + '"']
		opts.append('style=filled')
		opts.append('fillcolor=' + ('F' in self.attr and 'bisque' or
					('M' in self.attr and 'azure2' or 'white')))
		if self.group:
			opts.append('group=' + str(self.group))
		return self.id + '[' + ','.join(opts) + ']'

class Household:
	def __init__(self):
		self.parents = []
		self.kids = []
		self.id = 0
	
	def isempty(self):
		return len(self.parents) == 0 and len(self.kids) == 0

class Family:
	everybody = {}
	households = []
	layout_enforcer = LayoutRuleEnforcer()
	invisible = '[shape=circle,label="",height=0.01,width=0.01,fixedsize=true]';

	def add_person(self, string):
		p = Person(string)
		key = p.id
		if key in self.everybody:
			self.everybody[key].attr.update(p.attr)
		else:
			self.everybody[key] = p
		return self.everybody[key]

	def add_household(self, h):
		if len(h.parents) != 2:
			print('error: number of parents != 2', file=sys.stderr)
			return
		h.id = len(self.households)
		self.households.append(h)
		for p in h.parents:
			if not h in p.households:
				p.households.append(h)

	def find_person(self, name):
		if name in self.everybody:
			return self.everybody[name]
		for p in self.everybody.values():
			if p.name == name:
				return p
		return None
		
	def populate(self, f):
		h = Household()
		while True:
			line = f.readline()
			if line == '':
				if not h.isempty(): self.add_household(h)
				break
			line = line.rstrip()
			if line == '':
				if not h.isempty(): self.add_household(h)
				h = Household()
			elif line[0] == '#':
				continue
			else:
				if line[0] == '\t':
					p = self.add_person(line[1:])
					p.parents = h.parents
					h.kids.append(p)
				else:
					p = self.add_person(line)
					h.parents.append(p)

	def find_first_ancestor(self):
		for p in self.everybody.values():
			if len(p.parents) == 0:
				return p

	def next_generation(self, gen):
		next_gen = []
		for p in gen:
			if not p.follow_kids: continue
			for h in p.households:
				next_gen.extend(h.kids)
		return next_gen

	def get_spouse(household, person):
		return	household.parents[0] == person \
				and household.parents[1] or household.parents[0]

	def display_generation(self, gen):
		enforcer = Family.layout_enforcer
		def print_edge(src, dst, etype, opts=None):
			if opts is None: opts = []
			s, d = enforcer.enforce(src, dst, etype)
			print('\t\t%s -> %s [%s];' % (s, d, ','.join(opts)))

		# Assign vertical groups to middle children to force vertical lines
		for p in gen:
			for h in p.households:
				if len(h.kids) > 0:
					middle_idx = int(len(h.kids)/2)
					h.kids[middle_idx].group = h.id

		print('\t{ rank=same;')
		prev = None
		for p in gen:
			l = len(p.households)
			if prev:
				# Use weight to keep horizontal alignment tight
				target = p.id if l == 0 else Family.get_spouse(p.households[0], p).id
				print('\t\t%s -> %s [style=invis, weight=10];' % (prev, target))

			if l == 0:
				prev = p.id
				continue
			
			for i in range(0, int(l/2)):
				h = p.households[i]
				spouse = Family.get_spouse(h, p)
				print_edge(spouse.id, 'h%d' % h.id, 'spouse', ['color="black:white:black"'])
				print_edge('h%d' % h.id, p.id, 'spouse', ['color="black:white:black"'])
				print('\t\th%d%s;' % (h.id, Family.invisible))
			for i in range(int(l/2), l):
				h = p.households[i]
				spouse = Family.get_spouse(h, p)
				print_edge(p.id, 'h%d' % h.id, 'spouse', ['color="black:white:black"'])
				print_edge('h%d' % h.id, spouse.id, 'spouse', ['color="black:white:black"'])
				print('\t\th%d%s;' % (h.id, Family.invisible))
				prev = spouse.id
		print('\t}')

		print('\t{ rank=same;')
		prev = None
		for p in gen:
			for h in p.households:
				if len(h.kids) == 0: continue
				if prev:
					print('\t\t%s -> h%d_0 [style=invis, weight=10];' % (prev, h.id))
				l = len(h.kids)
				if l % 2 == 0: l += 1
				for i in range(l - 1):
					print_edge('h%d_%d' % (h.id, i), 'h%d_%d' % (h.id, i+1), 'horizontal')
				for i in range(l):
					print('\t\th%d_%d%s;' % (h.id, i, Family.invisible))
					prev = 'h%d_%d' % (h.id, i)
		print('\t}')

		for p in gen:
			for h in p.households:
				if len(h.kids) > 0:
					print_edge('h%d' % h.id, 'h%d_%d' % (h.id, int(len(h.kids)/2)), 'vertical', ['group=%d' % h.id])
					i = 0
					for c in h.kids:
						opts = []
						if i == len(h.kids)/2: opts.append('group=%d' % h.id)
						print_edge('h%d_%d' % (h.id, i), c.id, 'vertical', opts)
						i += 1
						if i == len(h.kids)/2: i += 1

	def output_descending_tree(self, ancestor):
		gen = [ancestor]
		print('digraph {\n' + \
		      '\tgraph [splines=polyline, nodesep=0.8, ranksep=0.6, fontname = "Meiryo UI, MS Gothic, TakaoPGothic, IPAexGothic, sans-serif"];\n' + \
		      '\tnode [fontname = "Meiryo UI, MS Gothic, TakaoPGothic, IPAexGothic, sans-serif", shape=box, height=0.6, width=1.6, fixedsize=true];\n' + \
		      '\tedge [fontname = "Meiryo UI, MS Gothic, TakaoPGothic, IPAexGothic, sans-serif", dir=none];\n')
		for p in self.everybody.values():
			print('\t' + p.graphviz() + ';')
		print('')
		while gen:
			self.display_generation(gen)
			gen = self.next_generation(gen)
		print(Family.layout_enforcer.get_report())
		print('}')

def main():
	parser = argparse.ArgumentParser(description='Generates a family tree graph from a simple text file')
	parser.add_argument('-a', dest='ancestor', help='ancestor name or id')
	parser.add_argument('input', metavar='INPUTFILE', help='input text file')
	args = parser.parse_args()
	family = Family()
	try:
		with open(args.input, 'r', encoding='utf-8') as f:
			family.populate(f)
	except FileNotFoundError:
		print(f"Error: File {args.input} not found.", file=sys.stderr)
		sys.exit(1)

	if args.ancestor:
		ancestor = family.find_person(args.ancestor)
		if not ancestor:
			print(f'Error: Cannot find person "{args.ancestor}"', file=sys.stderr)
			sys.exit(1)
	else:
		ancestor = family.find_first_ancestor()

	if ancestor:
		family.output_descending_tree(ancestor)

if __name__ == '__main__':
	main()
