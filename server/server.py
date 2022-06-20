import socket, sys, pickle, hashlib, math, json, os
from threading import Thread

class ThreadGestionClient(Thread):
    'Gestion du Thread du Socket du client'
    def __init__(self, connexion, nom, repertoire):
        Thread.__init__(self) # Classe Thread
        self.connexion = connexion
        self.nom = nom
        self.repertoire = repertoire
        self.tailleHeader = 1024

    def envoyer(self, message):
        "Envois d'un message Pickle"
        message = pickle.dumps(message)
        messageHeader = str(len(message)).encode('utf-8')
        self.connexion.send(messageHeader)
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'recu':
            self.connexion.send(message)
        else:
            print('[ERREUR]: Reponse non attendue')

    def recevoir(self):
        "Reception d'un message Pickle"
        messageHeader = self.connexion.recv(self.tailleHeader)
        messageHeader = int(messageHeader.decode('Utf-8'))
        self.connexion.send('recu'.encode('Utf-8'))
        message = self.connexion.recv(messageHeader)
        return pickle.loads(message)

    def envoyerFichier(self, reponse):
        'Gestion du Téléchargement de fichier'
        fTaille, fNom, fHash = conversion(reponse['Taille']), reponse['Nom'], reponse['Hash']
        print()
        print("Téléchargement en cours")
        print("Fichier: {}".format(fNom))
        print("Taille: {} {}".format(fTaille[0], fTaille)[1])
        with open(self.repertoire+'/'+fNom, 'wb') as f: # Ouvre le fichier afin d'y écrire les données recues
            dataTotal = b''
            dl=0
            lecture = True
            while reponse['Taille'] > len(dataTotal): # Boucle tant que le fichier téléchargé est moins grand que la taille recue
                data = self.connexion.recv(200000) # Reception des données
                if not data:
                    break
                dataTotal += data
                dl = len(dataTotal)
                print('{}%'.format(round((dl*100)/int(reponse['Taille'])))) # % de téléchargement
                f.write(data) # Ecriture des données
            lecture = False
            if lecture == False:
                fMd5Telecharger = hashlib.md5(open(self.repertoire+'/'+fNom,'rb').read()).hexdigest() # Hash du fichier recu
                if fMd5Telecharger == fHash: # Vérification du Hash recu et celui téléchargé
                    print('Téléchargement terminé {}, hash check OK'.format(fNom))
                    self.connexion.send('Hash correspond'.encode('Utf-8'))
                    return 'Hash correspond'
                else:
                    print('Téléchargement terminé {} mais Hash: {} =/ {}.'.format(fNom, fMd5Telecharger, fHash))
                    self.connexion.send('Hash ne correspond pas'.encode('Utf-8'))
                    return 'Hash ne correspond pas'
            else:
                print('[ERREUR]: Problème détecté')
                return False

    def recevoirFichier(self, fichier):
        "Gestion d'Upload de fichier"
        fNom, fTaille, fChemin = os.path.basename(fichier['Nom']), os.path.getsize(fichier['Chemin']), fichier['Chemin']
        md5Fichier = hashlib.md5(open(fChemin,'rb').read()).hexdigest() # hash du fichier
        message = {'Nom': fNom, 'Taille' : fTaille, 'Hash': md5Fichier}
        self.envoyer(message)
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'ok':
            print()
            print("Upload en cours")
            print("Fichier: {}".format(fNom))
            print("Taille: {} {}".format(conversion(fTaille)[0], conversion(fTaille)[1]))
            with open(fChemin, 'rb') as f: # Ouvre le fichier afin de le lire et d'envoyer les données
                count, offset, tmpTaille = 200000, 0, fTaille
                while tmpTaille > 0: # Boucle tant que le fichier uploadé est plus grand que 0
                    data = self.connexion.sendfile(f, offset, count) # Envois du fichier 
                    offset += data
                    tmpTaille -= data # Pour l'affichage de la progression décrémente la taille
                    val = round((offset*100)/fTaille) # % de l'upload
                    print('{}%'.format(val))
            reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
            if reponse == 'Hash correspond':
                print('Upload terminé, hash OK {}.'.format(fNom))
                return 'Hash correspond'
            elif reponse == 'Hash ne correspond pas':
                print('Upload terminé {} mais le check du Hash ne correspond pas.'.format(fNom))
                return 'Hash ne correspond pas'
            else:
                print('[ERREUR]: Le client ne répond pas (1).')
                return False
        else:
            print('[ERREUR]: Le client ne répond pas (2).')
            return False

    def run(self):
        'Lancement du thread'
        while True:
            reponse = self.connexion.recv(self.tailleHeader).decode('Utf8')
            if not reponse or reponse =="quit":
                break
            if reponse =='envois': # Gestion reception de téléchargement de fichier
                print("Client {}, 'envois' recus.".format(self.nom))
                self.connexion.send('ok'.encode('Utf-8'))
                reponse = self.recevoir()
                self.connexion.send('ok'.encode('Utf-8'))
                reussie = self.envoyerFichier(reponse) # Gestion de la reception
                self.connexion.recv(self.tailleHeader)
                scan = scanRepertoire(os.path.basename(self.repertoire), self.repertoire,[]) # Met à jours le scan du repertoire
                scan.insert(0, {'Repertoire': self.repertoire}) 
                self.envoyer(scan) # Envois du scan au client
                if reussie == False:
                    print("[ERREUR]: Erreur de reception de fichier du client")
                    break
            elif reponse =='recevoir': # Gestion reception de upload de fichier
                print("Client {}, 'recevoir' recus.".format(self.nom))
                self.connexion.send('ok'.encode('Utf-8'))
                fichier = self.recevoir()
                self.connexion.send('ok'.encode('Utf-8'))
                reussie = self.recevoirFichier(fichier) # Gestion de l'upload
                if reussie == False:
                    print("[ERREUR]: Erreur d'envois de fichier au client")
                    break
        self.connexion.close()     
        print("Client {} déconnecté.".format(self.nom))
        print()

class Initialisation(object):
    'Initialisation des variables pour lancer le serveur'
    def __init__(self):
        print("Entrer 'Quit' pour quitter")
        print()
        self.qUserOuSrv()
        self.hote = self.qTypeSrv()
        self.port = self.qPort()
        self.repertoire = self.qRepertoire()
        if lireJs() == "N'existe pas":
            print("[ERREUR]: Aucun utilisateur enregistré")
            sys.exit()
        self.nvServeur = self.lancerSrv()

    def lancerSrv(self):
        'Préparation du lancement serveur'
        serveur = Serveur(self.hote, self.port, self.repertoire)  

    def checkQuitter(self, entrer):
        'Checker si quitter'
        if entrer.lower() == 'quit' or entrer.lower() == 'q':
            sys.exit()

    def qUserOuSrv(self):
        'Question Creer utilisateur ou Lancer serveur'
        entrer = input("Creer un utilisateur [1] ou démarrer un serveur [2] (défaut [2]): ")
        self.checkQuitter(entrer)
        if entrer == '1':
            nom = input('Nom: ')
            mdp = input('Mot de passe: ')
            self.nvUtilisateur(nom, mdp)

    def qTypeSrv(self):
        'Question si serveur local ou distant'
        entrer = input("Serveur local ou distant? [1][2] (défaut [1]): ")
        self.checkQuitter(entrer)
        if entrer == '2':
            return '' # Bind l'écoute sur toutes les interfaces réseaux
        return '127.0.0.1'

    def qPort(self):
        'Question du choix du port'
        while True:
            entrer = input("Port de connexion: ")
            self.checkQuitter(entrer)
            if entrer.isdigit():
                return entrer
            else:
                print("Port non valide")

    def qRepertoire(self):
        'Question du choix du repertoire de transfère'
        entrer = input("Configurer un repertoire ou repertoire courrant [1][2] (défaut [2]): ")
        self.checkQuitter(entrer)
        if entrer == '1':
            entrer = input("Repertoire de transfère: ")
            try: # Test si répertoire accessible
                scanRepertoire(os.path.basename(entrer), entrer, []) 
                return entrer
            except:
                print("Le repertoire n'est pas accessible")
                self.qRepertoire()
        else:
            return '.'

    def nvUtilisateur(self, nom, mdp):
        'Question enregistrement nouveau utilisateur'
        sauvegarde = lireJs()
        if sauvegarde == "N'existe pas":
            print("Création du fichier Data.json")
            with open("data.json","w+") as f:
                dico = {}
                dico['Utilisateur'] = {}
                json.dump(dico, f, indent=4)
            self.nvUtilisateur(nom, mdp)
        else:  
            sauvegarde['Utilisateur'].update({nom : mdp})
            with open("data.json","w+") as f:
                json.dump(sauvegarde, f, indent=4)

class Serveur(object):
    'Initialisation du serveur'
    def __init__(self, hote, port, repertoire):
        'Initialisation du serveur'
        self.hote = hote
        self.port = port
        self.repertoire = repertoire
        self.tailleHeader = 1024
        self.serveur()

    def serveur(self):
        "Lancement du serveur Socket"
        serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serveur.bind((self.hote, int(self.port)))
        except socket.error:
            print("Erreur: Impossible de lier le socket, changer de port.")
            sys.exit()
        if self.hote == '': # Afin de print l'adresse ip local du serveur si Distant (il se bind sur toutes les interfaces) 
            ip = socket.gethostbyname(socket.gethostname())
        else:
            ip = self.hote
        print()
        print("Serveur prêt, en attente de requêtes...")
        print("Adresse IP: {}".format(ip))
        print("Port d'écoute: {}".format(self.port))
        print("Repertoire: {}".format(self.repertoire)) # Défaut repertoire courrant 
        print()
        serveur.listen(5) # Active la reception des connexions, le paramètre est le nombre maximum de connexions pouvant être recues avant d'être acceptées
        while True:
            self.connexion, adresse = serveur.accept() # Reception de la connexion d'un client
            reponse = self.connexion.recv(self.tailleHeader).decode('Utf8')
            if reponse == 'connexion':
                print("Connexion recus, vérification des identifiants")
                verif = self.verification() # Vérification des identifiants
                if verif == 0:
                    self.connexion.close()
                else:          
                    nom = verif[1] # Nom de l'utilisateur après vérification des identifiants
                    scan = scanRepertoire(os.path.basename(self.repertoire), self.repertoire,[]) # Scan du répertoire local choisi
                    scan.insert(0, {'Repertoire': self.repertoire}) 
                    self.envoyer(scan) # Envois du répertoire au client
                    th = ThreadGestionClient(self.connexion, nom, self.repertoire).start() # Lancement d'un thread avec la connexion du client
                    print("Client: {} connecté, adresse IP {}, port {}.".format\
                        (nom, adresse[0], adresse[1]))
                    print()
            else:
                print("[ERREUR]: Connexion invalide recue")
                self.connexion.close()

    def envoyer(self, message):
        "Envois d'un message Pickle"
        message = pickle.dumps(message)
        messageHeader = str(len(message)).encode('utf-8')
        self.connexion.send(messageHeader)
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'recu':
            self.connexion.send(message)
        else:
            print('[ERREUR]: Reponse non attendue')

    def recevoir(self):
        "Reception d'un message Pickle"
        messageHeader = self.connexion.recv(self.tailleHeader)
        messageHeader = int(messageHeader.decode('Utf-8'))
        self.connexion.send('recu'.encode('Utf-8'))
        message = self.connexion.recv(messageHeader)
        return pickle.loads(message)

    def verification(self):
        "Vérification des identifiants recus du Client"
        identifiants = lireJs()
        self.connexion.send('ok'.encode('Utf-8'))
        reponse = self.recevoir()
        nom, mdp = reponse['Identifiant'], reponse['Motdepasse']
        if nom in identifiants['Utilisateur']:
            if mdp == identifiants['Utilisateur'][nom]:
                self.connexion.send('Connexion réussie'.encode('Utf-8'))
                print('Connexion réussie')
                return 1, nom
            else:
                self.connexion.send('Mot de passe incorrect'.encode('Utf-8'))
                print('Mot de passe incorrect')
                return 0
        else:
            self.connexion.send('Identifiant incorrect'.encode('Utf-8'))
            print('Identifiant incorrect')
            return 0

def lireJs():
    "Lecture d'un fichier JSON"
    try:
        with open("data.json","r") as f:
            data = json.load(f)
        return data
    except:
        print("Le fichier 'data.json' n'existe pas")
        return "N'existe pas"

def scanRepertoire(racine, repertoire, l=[]):
    "Scan de repertoire local"
    l = l
    for i in os.scandir(repertoire):
        if not str(i).startswith('.'): # Ne pas gérer les fichiers cachés
            f = {}
            if i.is_dir():
                f['type'], f['nom'], f['chemin'] = 'dossier', os.path.basename(i.path), i.path
                l.append(f)
                scanRepertoire(racine, i.path, l)
            else:
                f['type'], f['nom'], f['chemin'] = 'fichier', os.path.basename(i.path), i.path
                if racine == os.path.basename(os.path.dirname(i.path)):
                    f['taille'], f['dossier'] = conversion(os.path.getsize(i.path)), '.'
                else:
                    f['taille'], f['dossier'] = conversion(os.path.getsize(i.path)), os.path.basename(os.path.dirname(i.path))
                l.append(f)
    return l

def conversion(nbr):
    'Convertis les valeurs dans leurs unités respectives'
    unités = ['Octets', 'Ko', 'Mo', 'Go', 'To'];
    if (nbr == 0):
        return '0 Octets'
    i = int(math.floor(math.log(nbr) / math.log(1000)))
    valeur = round(nbr / math.pow(1000, i), 2)
    return valeur, unités[i]

lancement = Initialisation()
