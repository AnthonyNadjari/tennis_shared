import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime, timedelta

# Configuration
day = '27'
hours = 19  # 7 PM
minutes = 0


def timer(t):
    target_time = datetime.strptime(t, "%H:%M").replace(
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day
    )
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)


# Setup Chrome
service = Service(executable_path=r'C:\Users\x01376312\Downloads\chromedriver.exe')
options = webdriver.ChromeOptions()
options.page_load_strategy = 'eager'
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)


def enter_data(xpath, keys):
    wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
    driver.find_element(By.XPATH, xpath).send_keys(keys, Keys.RETURN)


def click_on(xpath):
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.find_element(By.XPATH, xpath).click()


def check_slot_duration():
    """Check if the selected slot has 1-hour option available"""
    try:
        time.sleep(1)  # Wait for booking page to load

        # Find the select element
        select_element = driver.find_element(By.ID, "booking-duration")
        options = select_element.find_elements(By.TAG_NAME, "option")

        print(f"📋 Found {len(options)} duration option(s)")

        # If only one option, it's a 30-minute slot
        if len(options) == 1:
            print("⏭️ Only 30-minute slot available")
            return False

        # If we have multiple options, we can book 1 hour
        print("✅ Multiple duration options available - can book 1 hour")
        return True

    except Exception as e:
        print(f"⚠️ Could not check duration: {e}")
        return False


def close_booking_modal():
    """Close the booking modal to return to slot selection"""
    try:
        # Try different ways to close the modal
        close_methods = [
            # Try clicking outside the modal
            lambda: driver.execute_script("document.querySelector('.modal-backdrop, .overlay').click()"),
            # Try ESC key
            lambda: driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE),
            # Try close button
            lambda: driver.find_element(By.CSS_SELECTOR, ".close, .modal-close, [data-dismiss='modal']").click(),
            # Try cancel button
            lambda: driver.find_element(By.XPATH,
                                        "//button[contains(text(), 'Cancel') or contains(text(), 'Back')]").click()
        ]

        for method in close_methods:
            try:
                method()
                time.sleep(0.5)
                # Check if modal is closed by looking for booking links again
                if driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked"):
                    print("✅ Modal closed successfully")
                    return True
            except:
                continue

        print("⚠️ Could not close modal with standard methods")
        return False

    except Exception as e:
        print(f"⚠️ Error closing modal: {e}")
        return False


try:
    ## Login
    print("🔐 Starting login process...")
    driver.get(
        r"https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
    click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button')
    enter_data('//*[@id="154:0"]', 'anthonadj')
    enter_data('//*[@id="input-2"]', 'SorLouise2!')
    print("✅ Login completed")

    ## Select date
    print(f"📅 Selecting day: {day}")
    click_on('//*[@id="book-by-date-view"]/div/div[1]/div/div[1]/button')
    dates = driver.find_elements(By.CSS_SELECTOR, 'td[data-handler="selectDay"]')
    for d in dates:
        if d.text == day:
            d.click()
            break
    print("✅ Date selected")

    ### COURT FINDING WITH RETRY LOGIC ###
    driver.refresh()

    # Just wait for any booking elements to appear (or not)
    time.sleep(1)  # Quick wait for refresh

    # Calculate target time in minutes
    target_time_minutes = hours * 60 + minutes
    hour_str = f"{hours:02d}:{minutes:02d}"
    print(f"🔍 Looking for slot at {hour_str} ({target_time_minutes} minutes)")

    # Retry logic - max 5 minutes
    start_time = time.time()
    max_duration = 5 * 60  # x hours in seconds
    attempt = 0
    slot_found = False
    timer("19:59")

    while time.time() - start_time < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        print(f"🔄 Attempt {attempt} (elapsed: {elapsed}s)")

        # Get all available booking links
        booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
        if not booking_links or len(booking_links)==0:
            print("⚠️ No booking slots available on page")
        else:
            # Find all slots at target time
            target_slots = []
            for link in booking_links:
                data_test_id = link.get_attribute('data-test-id') or ""
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3:
                        try:
                            slot_time = int(parts[2])
                            if slot_time == target_time_minutes:
                                target_slots.append(link)
                        except:
                            continue

            print(f"🎯 Found {len(target_slots)} slot(s) at {hour_str}")

            # Try each slot at the target time
            for i, slot in enumerate(target_slots):
                print(f"🔍 Checking slot {i + 1}/{len(target_slots)}")

                try:
                    slot.click()
                    print("✅ Slot clicked, checking duration...")

                    if check_slot_duration():
                        print("✅ 1-hour slot confirmed!")
                        slot_found = True
                        break
                    else:
                        print(f"⏭️ Slot {i + 1} is 30-minute, closing modal...")
                        if close_booking_modal():
                            print("✅ Modal closed, trying next slot...")
                            time.sleep(0.5)  # Brief pause before trying next slot
                        else:
                            print("⚠️ Could not close modal, refreshing page...")
                            driver.refresh()
                            time.sleep(1)
                            break  # Break from slot loop to refresh

                except Exception as e:
                    print(f"⚠️ Error with slot {i + 1}: {e}")
                    continue

            if slot_found:
                break  # Exit the main retry loop

            if len(target_slots) > 0:
                print(f"❌ All {len(target_slots)} slots at {hour_str} are 30-minute slots")

        # If no suitable slot found and still have time, refresh and try again
        remaining_time = max_duration - (time.time() - start_time)
        if remaining_time > 5:
            print(f"🔄 Refreshing page to look for new slots... ({int(remaining_time)}s remaining)")
            driver.refresh()
            time.sleep(1)
        else:
            print("⏰ Time limit reached, stopping search")
            break

    # Check if slot was found
    if not slot_found:
        print(f"❌ No slot found for {hour_str} after 5 minutes")
        driver.quit()
        exit()

    click_on('/html/body/div[8]/div/div/div/div[1]/form/div[1]/div[1]/div[2]/div/div/div/span')
    click_on('/html/body/span/span/span[2]/ul/li[2]')
    click_on('//*[@id="submit-booking"]')
    click_on('//*[@id="paynow"]')
    time.sleep(0.5)
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '5354562794845156')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '0430')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '666')

    try:
        print("💳 Attempting to submit payment...")
        click_on('//*[@id="cs-stripe-elements-submit-button"]')
        print("✅ Payment button clicked successfully")

        # Wait and check what happens
        for i in range(10):  # Check for 10 seconds
            time.sleep(0.5)
            current_url = driver.current_url
            print(f"⏰ Second {i + 1}: Current URL: {current_url}")

            # Check if we're on a success/confirmation page
            if "success" in current_url.lower() or "confirmation" in current_url.lower() or "thank" in current_url.lower():
                print("🎉 Payment appears successful - on confirmation page!")
                break

            # Check if still on payment page
            if "payment" in current_url.lower() or "stripe" in current_url.lower():
                print("⚠️ Still on payment page...")

            # Check page content for success messages
            page_source = driver.page_source.lower()
            if "booking confirmed" in page_source or "payment successful" in page_source:
                print("🎉 Success message found on page!")
                time.sleep(5)
                break

        print("🎉 Booking process completed!")

    except Exception as e:
        print(f"❌ Payment submission error: {e}")
        # Take a screenshot to see what's happening
        try:
            driver.save_screenshot("payment_error.png")
            print("📸 Screenshot saved as payment_error.png")
        except:
            pass

except Exception as e:
    print(f"❌ Error occurred: {e}")
finally:
    # driver.quit()
    print("✅ Browser closed")