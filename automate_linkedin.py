import argparse
import pandas as pd
import pprint
import uuid
import os
import time
from pathlib import Path

import pyautogui
from wsConnectionHandler import WsConnectionHandler

LOCATOR_IMG_DIR = Path(__file__).parent / 'locator_images'

connection_handler = WsConnectionHandler('localhost', 8765)


def trigger_extension():
    """
    This function is to trigger the browser extension to make it listen for commands from the server.
    """

    time.sleep(1.0)  # wait 2 second for the browser to load
    pyautogui.hotkey('alt', 'shift', 'l')  # to trigger the extension
    time.sleep(1.0)
    pyautogui.hotkey('alt', 'l')  # to trigger the extension
    time.sleep(2.0)  # wait 2 seconds for the websocket connection to establish with browser extension


def close_extension():
    """
    This function closes the extension popup, thus disconnecting the websocket connection.
    """
    pyautogui.hotkey('alt', 'shift', 'l')  # to trigger the extension


def is_firefox_running():
    check_running_command = "ps -U tuhin | grep firefox"
    output = os.popen(check_running_command).read()
    return True if output else False


def search_company_name(company_name: str):
    pyautogui.typewrite(company_name, interval=0.03)
    pyautogui.press('enter')

    time.sleep(5)  # let it load the results


def get_results_count():
    """
    Get the number of pages of search results.
    """
    trigger_extension()
    css_selector = "div.search-results-container>div>h2"
    connection_handler.ask_browser(
        [
            {"command_id": str(uuid.uuid4()), "operation": "getElemAttribute", 'attribute': 'innerText',
             "selector": css_selector},
        ]
    )
    result = 0
    for response in connection_handler.get_responses():
        if response.get('messageType') == 'sniffingResult':
            data = response.get('data', " ")
            result = int(data.split(' ')[0])
            break

    # close_extension()
    return result


def get_pages_count():
    max_page_css_selector = "li.artdeco-pagination__indicator--number:last-child"
    connection_handler.ask_browser(
        [
            {"command_id": str(uuid.uuid4()), "operation": "getElemAttribute", 'attribute': 'innerText',
             "selector": max_page_css_selector},
        ]
    )
    result = 0
    for response in connection_handler.get_responses():
        if response.get('messageType') == 'sniffingResult':
            data = response.get('data', " ")
            result = int(data)
            break

    return result


def get_all_people_in_page():
    # trigger_extension()
    people_name_css_selector = "span.entity-result__title-line>span>a"
    people_name_list = []
    connection_handler.ask_browser(
        [
            {"command_id": str(uuid.uuid4()), "operation": "getAll", 'attribute': 'innerText',
             "selector": people_name_css_selector},
        ]
    )

    for response in connection_handler.get_responses():
        if response.get('messageType') == 'sniffingResult':
            data = response.get('data', '')
            for people_name in data:
                people_name_list.append(people_name.strip('\n ').split('\n')[0].strip())
    # close_extension()

    pprint.PrettyPrinter(indent=2).pprint(people_name_list)
    return people_name_list


def people_profile_links():
    # trigger_extension()

    people_profile_css_selector = "span.entity-result__title-line>span>a"
    profile_links_list = []
    connection_handler.ask_browser(
        [
            {"command_id": str(uuid.uuid4()), "operation": "getAll", 'attribute': 'href',
             "selector": people_profile_css_selector},
        ]
    )

    for response in connection_handler.get_responses():
        if response.get('messageType') == 'sniffingResult':
            data = response.get('data')
            for profile_link in data:
                profile_links_list.append(profile_link.strip())

    close_extension()
    pprint.PrettyPrinter(indent=2).pprint(profile_links_list)
    return profile_links_list


def go_to_next_page():
    # press pgdn 2 times
    pyautogui.hotkey('ctrl', 'end')

    time.sleep(0.5)

    button_location = pyautogui.locateOnScreen(str(LOCATOR_IMG_DIR / 'next_button.png'), confidence=0.8)
    print("next button location:", button_location)
    pyautogui.click(button_location)  # click on next button

    time.sleep(5)  # let it load the results


# Open a web browser to the LinkedIn sign-in page.
def open_linkedin(company_name: str):
    is_running = is_firefox_running()
    if not is_running:
        pyautogui.hotkey('win')
        pyautogui.typewrite('firefox')
        pyautogui.press('enter')
    else:
        pyautogui.hotkey('alt', 'tab')

    # TODO: get information from extension, whether the tab is already open or not

    pyautogui.hotkey('alt', 'tab')  # back to pycharm
    inp = input("Tab already open ? (y/n): ")
    if inp == 'n':
        pyautogui.hotkey('alt', 'tab')  # back to firefox window

        time.sleep(3)  # for browser to open
        pyautogui.hotkey('ctrl', 'shift', '5')  # for firefox multi account container profile - 1
        time.sleep(0.5)

        pyautogui.typewrite('https://www.linkedin.com/feed/', interval=0.05)
        pyautogui.press('enter')
        time.sleep(5)  # for feed to load completely
    else:
        pyautogui.hotkey('alt', 'tab')  # back to browser window

    search_button_location = pyautogui.locateOnScreen(str(LOCATOR_IMG_DIR / 'search_button.png'), confidence=0.5)
    print(search_button_location)
    pyautogui.click(search_button_location)  # click on search button

    search_company_name(company_name)

    people_capsule_location = pyautogui.locateOnScreen(str(LOCATOR_IMG_DIR / 'people_capsule.png'), confidence=0.6)
    print(people_capsule_location)
    pyautogui.click(people_capsule_location)  # click on people capsule

    results_count = get_results_count()
    pages_count = get_pages_count()

    scrap_df = pd.DataFrame(columns=['name', 'profile_link'])

    for page_ind in range(pages_count):
        print(f"\n-----------------------------Page {page_ind + 1} of {pages_count}------------------------\n")

        people_name_list = get_all_people_in_page()
        profile_links_list = people_profile_links()

        if len(people_name_list) != len(profile_links_list):
            print("Length of people name list and profile links list are not equal.")
            # fix the length of the lists, add None to the shorter list
            if len(people_name_list) > len(profile_links_list):
                profile_links_list += [None] * (len(people_name_list) - len(profile_links_list))
            else:
                people_name_list += [None] * (len(profile_links_list) - len(people_name_list))

        # merge the 2 lists as 2 columns
        df = pd.DataFrame({'name': people_name_list, 'profile_link': profile_links_list})
        scrap_df = pd.concat([scrap_df, df], ignore_index=True)

        scrap_df.to_csv('scrap.csv', index=False)

        go_to_next_page()

        trigger_extension()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--company', type=str, help='Company name to search for.')
    args = parser.parse_args()

    connection_handler.connect_server()
    open_linkedin(args.company)
