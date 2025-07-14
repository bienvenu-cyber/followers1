import requests
import random
import string
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from followers.email_fallback import get_email_and_code_fallback

CONFIG_PATH = 'config/bots_credentials.json'
LOG_PATH = 'signup_log.txt'
LOG_JSON_PATH = 'signup_errors.json'
SCREENSHOT_DIR = 'screenshots'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Liste de user-agents réalistes (mobile et desktop)
USER_AGENTS = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Mobile
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# Blacklist temporaire des domaines email ayant échoué
EMAIL_DOMAIN_BLACKLIST = set()

# --------- Email Service Abstractions ---------
class EmailService:
    def generate_email(self):
        raise NotImplementedError
    def get_verification_code(self, email, timeout=120):
        raise NotImplementedError

# 1secmail implementation
class OneSecMail(EmailService):
    def generate_email(self):
        login = random_string(10)
        domain = random.choice(['1secmail.com', '1secmail.org', '1secmail.net'])
        email = f"{login}@{domain}"
        return {'email': email, 'login': login, 'domain': domain}
    def get_verification_code(self, email_obj, timeout=300):
        import re
        login = email_obj['login']
        domain = email_obj['domain']
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
        for _ in range(timeout // 5):
            try:
                resp = requests.get(url, timeout=10)
                log(f"[DEBUG] 1secmail API response: {resp.text}", level='DEBUG')
                messages = resp.json()
                for msg in messages:
                    if 'Instagram' in msg['from']:
                        mail_id = msg['id']
                        mail_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={mail_id}"
                        mail_resp = requests.get(mail_url, timeout=10).json()
                        # Chercher le code dans le sujet
                        match = re.search(r'(\\d{6})', msg.get('subject', ''))
                        if match:
                            log(f"[INFO] Code trouvé dans le sujet : {match.group(1)}")
                            return match.group(1)
                        # Chercher le code dans le corps
                        match = re.search(r'(\\d{6})', mail_resp.get('body', ''))
                        if match:
                            log(f"[INFO] Code trouvé dans le corps du mail : {match.group(1)}")
                            return match.group(1)
            except Exception as e:
                log(f"[1secmail] Erreur API: {e}", level='ERROR')
            time.sleep(5)
        log(f"[ALERTE] Aucun mail Instagram reçu sur {login}@{domain} après 5 minutes. Vérifiez manuellement sur https://www.1secmail.com/")
        log(f"[ALERTE] Le domaine {domain} est peut-être blacklisté par Instagram.")
        return None

# mail.tm implementation
class MailTm(EmailService):
    def __init__(self):
        self.base_url = "https://api.mail.tm"
        self.session = requests.Session()
    def generate_email(self):
        password = random_string(12)
        domains = self.session.get(f"{self.base_url}/domains").json()['hydra:member']
        domain = random.choice(domains)['domain']
        local = random_string(10)
        address = f"{local}@{domain}"
        resp = self.session.post(f"{self.base_url}/accounts", json={"address": address, "password": password})
        if resp.status_code != 201:
            raise Exception(f"mail.tm: Impossible de créer le compte mail ({resp.text})")
        token = self.session.post(f"{self.base_url}/token", json={"address": address, "password": password}).json()['token']
        self.session.headers.update({'Authorization': f'Bearer {token}'})
        return {'email': address, 'password': password}
    def get_verification_code(self, email_obj, timeout=300):
        import re
        for _ in range(timeout // 5):
            try:
                resp = self.session.get(f"{self.base_url}/messages")
                log(f"[DEBUG] mail.tm API response: {resp.text}", level='DEBUG')
                messages = resp.json()['hydra:member']
                for msg in messages:
                    if 'Instagram' in msg['from']['address']:
                        msg_id = msg['id']
                        mail_resp = self.session.get(f"{self.base_url}/messages/{msg_id}").json()
                        # Chercher le code dans le sujet
                        match = re.search(r'(\\d{6})', msg.get('subject', ''))
                        if match:
                            log(f"[INFO] Code trouvé dans le sujet : {match.group(1)}")
                            return match.group(1)
                        # Chercher le code dans le corps
                        match = re.search(r'(\\d{6})', mail_resp.get('text', ''))
                        if match:
                            log(f"[INFO] Code trouvé dans le corps du mail : {match.group(1)}")
                            return match.group(1)
            except Exception as e:
                log(f"[mail.tm] Erreur API: {e}", level='ERROR')
            time.sleep(5)
        log(f"[ALERTE] Aucun mail Instagram reçu sur {email_obj['email']} après 5 minutes. Vérifiez manuellement sur https://mail.tm/")
        log(f"[ALERTE] Le domaine {email_obj['email'].split('@')[1]} est peut-être blacklisté par Instagram.")
        return None

# --------- Utilitaires ---------
def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def log(msg, level='INFO'):
    print(f'[{level}] {msg}')
    with open(LOG_PATH, 'a') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {msg}\n")
    # Log structuré pour les erreurs
    if level in ('ERROR', 'ERREUR'):
        entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'message': msg
        }
        try:
            if not os.path.exists(LOG_JSON_PATH):
                with open(LOG_JSON_PATH, 'w') as jf:
                    json.dump([entry], jf, indent=2)
            else:
                with open(LOG_JSON_PATH, 'r+') as jf:
                    data = json.load(jf)
                    data.append(entry)
                    jf.seek(0)
                    json.dump(data, jf, indent=2)
        except Exception as e:
            print(f'[LOG ERROR] Impossible d\'écrire dans {LOG_JSON_PATH}: {e}')

def save_bot_credentials(username, password):
    if not os.path.exists(CONFIG_PATH):
        data = {"bots": []}
    else:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
    data['bots'].append({"username": username, "password": password})
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=4)
    log(f"Identifiants ajoutés à {CONFIG_PATH}")

def take_screenshot(browser, step):
    ts = time.strftime('%Y%m%d_%H%M%S')
    path = os.path.join(SCREENSHOT_DIR, f'{step}_{ts}.png')
    browser.save_screenshot(path)
    log(f'[SCREENSHOT] {path}')

def wait_and_fill(browser, by, selector, value, timeout=30):
    import random
    import string
    try:
        elem = WebDriverWait(browser, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        elem.clear()
        # Simulation de frappe humaine avec erreurs et corrections
        for char in value:
            # Simuler une erreur de frappe 10% du temps
            if random.random() < 0.1:
                wrong_char = random.choice(string.ascii_lowercase)
                elem.send_keys(wrong_char)
                time.sleep(random.uniform(0.05, 0.15))
                elem.send_keys("\b")  # Correction (backspace)
                time.sleep(random.uniform(0.05, 0.15))
            elem.send_keys(char)
            time.sleep(random.uniform(0.07, 0.18))
        return True
    except Exception as e:
        log(f'[ERREUR] Impossible de remplir {selector}: {e}', level='ERROR')
        take_screenshot(browser, f'fail_fill_{selector}')
        return False

def wait_and_click(browser, by, selector, timeout=30):
    import random
    try:
        elem = WebDriverWait(browser, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
        # Mouvement de souris aléatoire avant le clic
        actions = ActionChains(browser)
        x_offset = random.randint(-10, 10)
        y_offset = random.randint(-5, 5)
        actions.move_to_element_with_offset(elem, x_offset, y_offset).pause(random.uniform(0.2, 0.6)).perform()
        time.sleep(random.uniform(0.1, 0.4))
        elem.click()
        return True
    except Exception as e:
        log(f'[ERREUR] Impossible de cliquer {selector}: {e}', level='ERROR')
        take_screenshot(browser, f'fail_click_{selector}')
        return False

def handle_birthday_page(browser):
    # Essayer plusieurs variantes de sélecteurs pour la date de naissance
    selectors = [
        # Français
        {'day': (By.XPATH, "//select[@title='Jour :']"), 'month': (By.XPATH, "//select[@title='Mois :']"), 'year': (By.XPATH, "//select[@title='Année :']")},
        # Anglais
        {'day': (By.XPATH, "//select[@title='Day:']"), 'month': (By.XPATH, "//select[@title='Month:']"), 'year': (By.XPATH, "//select[@title='Year:']")},
        # Autres variantes possibles
    ]
    for sel in selectors:
        try:
            day = browser.find_element(*sel['day'])
            month = browser.find_element(*sel['month'])
            year = browser.find_element(*sel['year'])
            Select(day).select_by_value("1")
            Select(month).select_by_value("1")
            Select(year).select_by_value("2000")
            # Bouton suivant : plusieurs variantes
            next_btns = [
                (By.XPATH, "//button[@type='button' and (text()='Suivant' or text()='Next')]") ,
                (By.XPATH, "//button[contains(.,'Suivant') or contains(.,'Next')]")
            ]
            for by, sel_btn in next_btns:
                try:
                    btn = browser.find_element(by, sel_btn)
                    btn.click()
                    log("[INFO] Date de naissance renseignée et validée.", level='INFO')
                    time.sleep(2)
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    take_screenshot(browser, 'fail_birthday')
    log('[ERREUR] Impossible de remplir la date de naissance.', level='ERROR')
    return False

def handle_popups(browser):
    # Fermer les popups éventuels (cookies, overlays, etc.)
    popups = [
        (By.XPATH, "//button[contains(.,'Accepter') or contains(.,'Accept')]"),
        (By.XPATH, "//button[contains(.,'Refuser') or contains(.,'Refuse')]"),
        (By.XPATH, "//button[contains(.,'Plus tard') or contains(.,'Later')]"),
    ]
    for by, sel in popups:
        try:
            btn = browser.find_element(by, sel)
            btn.click()
            log('[INFO] Popup fermé.', level='INFO')
            time.sleep(1)
        except Exception:
            continue

def simulate_human_navigation(browser):
    import random
    log('[HUMAN] Début de la navigation humaine simulée...', level='INFO')
    browser.get('https://www.instagram.com/')
    time.sleep(random.randint(2, 5))
    take_screenshot(browser, 'home_page')
    # Accepter les cookies si popup
    try:
        btn = browser.find_element(By.XPATH, "//button[contains(.,'Accepter') or contains(.,'Accept')]")
        btn.click()
        log('[HUMAN] Cookies acceptés.', level='INFO')
        time.sleep(1)
    except Exception:
        pass
    # Scroller la page
    for _ in range(random.randint(2, 4)):
        browser.execute_script("window.scrollBy(0, 500);")
        time.sleep(random.randint(1, 3))
    take_screenshot(browser, 'after_scroll')
    # Mouvements de souris aléatoires
    actions = ActionChains(browser)
    for _ in range(random.randint(3, 7)):
        x = random.randint(0, 800)
        y = random.randint(0, 600)
        try:
            actions.move_by_offset(x, y).perform()
            log(f'[HUMAN] Souris déplacée vers ({x},{y})', level='INFO')
            time.sleep(random.uniform(0.2, 1.2))
        except Exception:
            continue
    # Cliquer sur quelques liens du footer (toujours relocaliser avant chaque clic)
    footer_links = [
        "À propos", "Blog", "Emplois", "Aide", "API", "Confidentialité", "Conditions", "About", "Blog", "Jobs", "Help", "API", "Privacy", "Terms"
    ]
    random.shuffle(footer_links)
    for link_text in footer_links[:2]:
        try:
            # Relocaliser les liens à chaque fois
            links = browser.find_elements(By.TAG_NAME, 'a')
            for link in links:
                if link_text.lower() in link.text.lower():
                    try:
                        actions.move_to_element(link).perform()
                        time.sleep(random.uniform(0.3, 1.0))
                        link.click()
                        log(f'[HUMAN] Lien cliqué : {link.text}', level='INFO')
                        time.sleep(random.randint(2, 4))
                        take_screenshot(browser, f'clicked_{link_text}')
                        browser.back()
                        time.sleep(1)
                        break  # On ne clique qu'un lien par texte
                    except Exception:
                        continue
        except Exception:
            continue
    # Navigation plus variée : aller sur une page d'aide ou de blog
    try:
        help_link = browser.find_element(By.PARTIAL_LINK_TEXT, 'Aide')
        actions.move_to_element(help_link).perform()
        help_link.click()
        log('[HUMAN] Page d\'aide visitée.', level='INFO')
        time.sleep(random.randint(2, 5))
        browser.back()
    except Exception:
        pass
    log('[HUMAN] Fin de la navigation humaine simulée.', level='INFO')
    time.sleep(random.randint(2, 5))

# --------- Instagram Automation ---------
def create_instagram_account(email, full_name, username, password):
    import random
    options = Options()
    # Rotation user-agent
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        simulate_human_navigation(browser)
        browser.get("https://www.instagram.com/accounts/emailsignup/")
        time.sleep(5)
        handle_popups(browser)
        if not wait_and_fill(browser, By.NAME, "emailOrPhone", email):
            return None
        if not wait_and_fill(browser, By.NAME, "fullName", full_name):
            return None
        if not wait_and_fill(browser, By.NAME, "username", username):
            return None
        if not wait_and_fill(browser, By.NAME, "password", password):
            return None
        if not wait_and_click(browser, By.XPATH, "//button[@type='submit']"):
            return None
        log("[INFO] Formulaire soumis. Gestion de la page de date de naissance...", level='INFO')
        for _ in range(40):
            handle_popups(browser)
            try:
                code_input = browser.find_element(By.NAME, "email_confirmation_code")
                return browser
            except NoSuchElementException:
                pass
            if handle_birthday_page(browser):
                continue
            time.sleep(2)
        take_screenshot(browser, 'fail_code_page')
        log("[ERREUR] Champ de code de validation non trouvé après gestion de la date de naissance.", level='ERROR')
        browser.quit()
        return None
    except Exception as e:
        take_screenshot(browser, 'fail_exception')
        log(f"[ERREUR] Selenium: {e}", level='ERROR')
        browser.quit()
        return None

def finalize_instagram_account(browser, code, username, password):
    try:
        code_input = browser.find_element(By.NAME, "email_confirmation_code")
        code_input.send_keys(code)
        log(f"[INFO] Code de validation injecté : {code}", level='INFO')
        take_screenshot(browser, 'after_code_input')
        time.sleep(1)
        # Essayer plusieurs variantes de boutons pour valider
        btn_selectors = [
            (By.XPATH, "//button[@type='button' and (text()='Suivant' or text()='Next' or text()='Valider')]") ,
            (By.XPATH, "//button[contains(.,'Suivant') or contains(.,'Next') or contains(.,'Valider')]")
        ]
        clicked = False
        for by, sel in btn_selectors:
            try:
                btn = browser.find_element(by, sel)
                btn.click()
                log("[INFO] Bouton de validation cliqué.", level='INFO')
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            log("[ALERTE] Aucun bouton de validation trouvé après saisie du code.", level='ALERT')
            take_screenshot(browser, 'fail_code_submit')
        time.sleep(3)
        take_screenshot(browser, 'after_code_submit')
        save_bot_credentials(username, password)
        log("[INFO] Compte créé et validé (ou tentative faite).", level='INFO')
        browser.quit()
        return True
    except Exception as e:
        take_screenshot(browser, 'fail_code_exception')
        log(f"[ERREUR] Validation: {e}", level='ERROR')
        browser.quit()
        return False

# --------- Orchestration multi-service ---------
def try_create_account_with_service(service, max_attempts=3):
    global EMAIL_DOMAIN_BLACKLIST
    for attempt in range(max_attempts):
        try:
            email_obj = service.generate_email()
            email = email_obj['email'] if isinstance(email_obj, dict) else email_obj
            domain = email.split('@')[1]
            if domain in EMAIL_DOMAIN_BLACKLIST:
                log(f"[EMAIL] Domaine {domain} blacklisté, on saute.", level='INFO')
                continue
            full_name = f"Bot {random_string(5)}"
            username = random_string(10)
            password = random_string(12)
            log(f"[INFO] Tentative {attempt+1} avec {service.__class__.__name__} : {email}", level='INFO')
            browser = create_instagram_account(email, full_name, username, password)
            if not browser:
                continue
            code = service.get_verification_code(email_obj)
            if not code:
                log(f"[ERREUR] Code de validation non reçu pour {email}. Blacklist temporaire du domaine {domain}.", level='ERROR')
                EMAIL_DOMAIN_BLACKLIST.add(domain)
                browser.quit()
                continue
            log(f"[INFO] Code reçu : {code}", level='INFO')
            success = finalize_instagram_account(browser, code, username, password)
            if success:
                return True
        except Exception as e:
            log(f"[ERREUR] {service.__class__.__name__}: {e}", level='ERROR')
    return False

if __name__ == "__main__":
    import sys
    print("=== MODE CONTINU 100% AUTO ===")
    n = 5  # Nombre de comptes par cycle (par défaut)
    interval = 10  # Intervalle entre chaque cycle (en minutes, par défaut)
    cycle = 1
    try:
        while True:
            log(f"\n=== Cycle {cycle} : Création de {n} comptes ===", level='INFO')
            comptes_crees = 0
            echecs = 0
            for i in range(n):
                log(f"\n--- Création du compte {i+1}/{n} (cycle {cycle}) ---", level='INFO')
                # Utiliser le fallback robuste pour obtenir email/code/service
                result = get_email_and_code_fallback(timeout=300)
                if not result:
                    echecs += 1
                    log("[ERREUR] Impossible d'obtenir un email/code après tous les fallback. Attente 10 minutes avant de recommencer.", level='ERROR')
                    time.sleep(600)
                    break
                email, code, service_name = result
                # Générer nom, username, password
                full_name = f"Bot {random_string(5)}"
                username = random_string(10)
                password = random_string(12)
                log(f"[INFO] Utilisation du service {service_name} pour {email}", level='INFO')
                browser = create_instagram_account(email, full_name, username, password)
                if not browser:
                    echecs += 1
                    continue
                log(f"[INFO] Code reçu : {code}", level='INFO')
                success = finalize_instagram_account(browser, code, username, password)
                if success:
                    comptes_crees += 1
                else:
                    echecs += 1
                if i < n - 1:
                    delay = random.randint(30, 90)
                    log(f"[INFO] Pause de {delay} secondes avant la prochaine création...", level='INFO')
                    time.sleep(delay)
            # Résumé/statistiques du cycle
            log("\n=== Résumé du cycle {} ===".format(cycle), level='INFO')
            log(f"Comptes créés : {comptes_crees}/{n}", level='INFO')
            log(f"Échecs : {echecs}", level='INFO')
            log(f"[INFO] Cycle {cycle} terminé. Prochain cycle dans {interval} minutes.", level='INFO')
            cycle += 1
            time.sleep(interval * 60)
    except KeyboardInterrupt:
        log("[INFO] Arrêt manuel du script (Ctrl+C)", level='INFO')
        sys.exit(0) 