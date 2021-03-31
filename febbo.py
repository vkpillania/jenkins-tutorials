#!/usr/bin/python

def fibbo(number):
   i = 0 
   a,b  = 0 , 1 
   while i < number:
      a,b = b, a+b
      yield a  
      i = i + 1
l = [ x for x in fibbo(10) ]

print(l)

