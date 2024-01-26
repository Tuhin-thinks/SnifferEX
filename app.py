"""
Flask app to get requests from browser and send responses.
"""
import re
import json
import pprint

from flask import Flask, request

app = Flask(__name__)


@app.route('/save-unique-video-suggestions', methods=['POST'])
def save_unique_video_suggestions():
    print("A request was received from the browser.")
    parsed_json = request.get_json()
    pprint.PrettyPrinter(indent=4).pprint(parsed_json)
    video_suggestions_json = parsed_json['video_suggestions']
    video_suggestions = video_suggestions_json
    page_title = parsed_json['page_title']
    
    # make page title a valid file name
    page_title = re.sub(r'[^\w\s]', '', page_title)
    
    # save the video suggestion into a JSON file with name from page_url
    # for example, if page_url is https://www.youtube.com/watch?v=1, then save the video suggestions into a JSON file
    # named 1.json
    with open(f"{page_title}.json", 'w') as f:
        json.dump(video_suggestions, f, indent=4)
    
    return 'success'


@app.route('/', methods=['GET'])
def get():
    return 'success'


if __name__ == '__main__':
    app.run(debug=True, port=5000)
