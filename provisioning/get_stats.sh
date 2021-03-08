#!/bin/sh

# filter bots:
# zgrep -h -i -vE "googlebot|bingbot|msnbot|slurp|mediapartners-google" /var/log/apache2/access.log* | awk '{ print $1 } '| sort | uniq | wc -l

for i in `zgrep -h -i -vE "googlebot|bingbot|msnbot|slurp|mediapartners-google" /var/log/apache2/access.log* | awk '{ print $1 } '| sort | uniq `
do
    geoiplookup $i | head -1 | cut -d' ' -f 5-
done > 'countrynamelist.txt'

cat countrynamelist.txt | sort | uniq | while read line
do
    echo -n "$line:" ; grep -o -i "$line" countrynamelist.txt | wc -l
done > countrycount.txt

cp countrycount.txt "countrycount-$(date +%Y-%m-%d).log"
