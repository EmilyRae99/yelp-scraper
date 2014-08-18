#/usr/bin/python
from bs4 import BeautifulSoup
from urllib import urlopen
from urlparse import urlparse
import sys
import os
import csv

MAX_USERS = 1000
FIELD_NAMES = ('user_id', 'funny', 'cool', 'useful', 'restaurant', 'review')

# Make sure the page is a yelp user page in the reviews tab.
def is_valid_yelp_user_review_page(html):
	if "Yelp" not in html.title.text:
		return False
	if "All Reviews" not in html.body.h3.text:
		return False
	return True

def is_valid_yelp_user_friends_page(html):
	return True if "Friends" in html.body.h3.text else False

def has_next_page_of_reviews(soup):
	return soup.find('div', id='empty_reviews') is not None

def scrape_reviews_of_current_page(review_soup, dict_writer, user_id):
	for review in review_soup.find_all('div', class_='review clearfix'):
		ufc_soup = review.find_all('span', class_='count')
		useful = int(ufc_soup[0].text)
		funny  = int(ufc_soup[1].text)
		cool   = int(ufc_soup[2].text)
		if not funny:
			return False

		comment = review.find('div', class_='review_comment').text
		if comment.startswith('\n                '):
			comment = review.text[17:]

		restaurant = review.find('div', class_='biz_info').h4.a.text

		dict_writer.write(
			{"user_id": user_id,
			 "funny":funny,
			 "cool":cool,
			 "useful":useful,
			 "restaurant":restaurant,
			 "review":review})

	return True
def write_csv_header(file):
	writer = csv.DictWriter(file, fieldnames=FIELD_NAMES)
	headers = dict((n,n) for n in FIELD_NAMES)
	writer.writerow(headers)

def scrape_reviews_to_file(user_id, dict_writer):
	# Maybe apply review sort by sf here
	review_soup = BeautifulSoup(urlopen('http://www.yelp.com/user_details_reviews_self?%s&review_sort=funny' % user_id))
	assert(is_valid_yelp_user_review_page(review_soup))
	page_start = 0
	has_next_page_of_reviews = review_soup.find(id='review_lister_header')
	while has_next_page_of_reviews(review_soup):
		if not scrape_reviews_of_current_page(review_soup, dict_writer, user_id):
			break
		page_start += 10
		review_soup = BeautifulSoup(urlopen('http://www.yelp.com/user_details_reviews_self'
			'?%s&review_sort=funny&rec_pagestart=%d' % (user_id, page_start)))

def add_user_friends_to_list(user_id, users_to_visit):
	user_soup = BeautifulSoup(urlopen('http://www.yelp.com/user_details_friends?%s' % user_id))
	assert(is_valid_yelp_user_friends_page(user_soup))
	# num_user_friends = user_soup.find(class_='range-of-total')
	for friend in user_soup.find_all('div', class_='friend_box'):
		try:
			friend_location = friend.find(class_='user-location').text
			if friend_location != "San Francisco, CA":
				continue
			friend_url = urlparse(friend.find(class_='photo-box pb-ss').a.get('href'))
			users_to_visit.append(friend_url.query)
		except:
			print "Something went wrong with %s" % friend

def get_yelp_users(seen_users, users_to_visit, csv_file):
	f = open(csv_file, 'wb')
	# write_csv_header(f)
	writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
	writer.writeheader()
	while users_to_visit:
		user = users_to_visit.pop()
		if user in seen_users:
			continue

		seen_users.add(user)
		print "Getting friends for user: %s" % user
		print "# seen: %d\t# to visit: %d" % (len(seen_users), len(users_to_visit))
		if len(seen_users) > MAX_USERS:
			break;
		scrape_reviews_to_file(user, writer)
		add_user_friends_to_list(user, users_to_visit)
	f.close()
	return seen_users

def main():
	assert(len(sys.argv) == 3)
	url = urlparse(sys.argv[1])
	csv = sys.argv[2]
	seen_users = set()
	users_to_visit = []

	assert("www.yelp.com" in url.netloc)

	if "friends" not in url.path:
		print "moving to friends page"
		query = url.query
		url = urlparse("http://www.yelp.com/user_details_friends?%s" % query)
	user = url.query
	if "&" in user:
		user = url.query.split('&')
	users_to_visit.append(user)
	get_yelp_users(seen_users, users_to_visit, csv)

if __name__ == "__main__":
	main()