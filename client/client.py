from tkinter import *
from tkinter import filedialog, scrolledtext, messagebox, PhotoImage, Menu
import tkinter.ttk as ttk
import time, socket, pickle, os, math, queue, hashlib
from threading import Thread

class App(object):
    def __init__(self):
        'Constructeur de la fenêtre principale et initialisation des variables'
        self.root = Tk()
        self.root.title('Transfère de fichiers')
        self.tailleHeader = 1024 # Taille du Buffer du Socket
        self.cheminTelechargement, self.repertoireLocal = '.', [os.path.abspath('.')]
        self.fichierImg, self.imageImg, self.dossierImg = PhotoImage(file='images/fichier.png'),PhotoImage(file='images/image.png'), PhotoImage(file='images/dossier.png')
        self.creation_widgets()
        self.queue = queue.Queue() # Initialisation de la file d'attente pour gérer les requetes
        self.run, self.lancer = True, False
        self.root.mainloop()
        self.run = False # Arrêt du thread car False

    def creation_widgets(self):
        'Creation des boutons et widgets'
        self.menuBarre = Menu(self.root)
        self.root.config(menu=self.menuBarre)
        self.fileMenu = Menu(self.menuBarre)
        self.fileMenu.add_command(label="Ajouter un repertoire", command=self.ajouterRepertoire)
        self.fileMenu.add_command(label="Répertoire de téléchargement", command=self.repertoireTelechargement)
        self.menuBarre.add_cascade(label="Fichier", menu=self.fileMenu)
        aide = Menu(self.menuBarre)
        aide.add_command(label="A propos", command=self.aide)
        self.menuBarre.add_cascade(label="Aide", menu=aide)

        self.boutons = Frame(self.root)
        self.boutons.grid(row=0, column=0, sticky='nswe', padx=10) 
        Label(self.boutons, text = "Identifiant:").\
                    grid(row =0, column =0)
        self.identifiantEntry = Entry(self.boutons)
        self.identifiantEntry.grid(row =0, column =1)
        Label(self.boutons, text = "Mot de passe:").\
                    grid(row =0, column =2)
        self.motdepasseEntry = Entry(self.boutons, show="*")
        self.motdepasseEntry.grid(row =0, column =3)
        Label(self.boutons, text = "Serveur:").\
                    grid(row =0, column =4)
        self.serveurEntry = Entry(self.boutons)
        self.serveurEntry.grid(row =0, column =5)
        Label(self.boutons, text = "Port:").\
                    grid(row =0, column =6)
        self.portEntry = Entry(self.boutons, width=7)
        self.portEntry.grid(row =0, column =7)
        Button(self.boutons, text ='Connexion', command =self.connexion).\
                    grid(row =0, column =8, padx=5) 

        # Gestion redimensionnement
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Frame 1 -- log --
        self.log = LabelFrame(self.root, text="Log", padx=5, pady=5)
        self.log.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')    
        self.log.rowconfigure(0, weight=1)
        self.log.columnconfigure(0, weight=1)
        self.scroll = scrolledtext.ScrolledText(self.log, width=40, height=5)
        self.scroll.grid(row=0, column=0,   sticky='nsew')
        self.scroll.tag_config('erreur', foreground="red")
        self.scroll.tag_config('réussie', foreground="green")

        # Frame 2 -- Parcourir fichier --
        self.parcourir = Frame(self.root)
        self.parcourir.grid(row=2, column=0, sticky='ew')
        self.parcourir.columnconfigure(0, weight=1)
        self.parcourir.columnconfigure(1, weight=1)

        # Frame 2 -- Parcourir : Local --
        self.local = LabelFrame(self.parcourir, text="Local", padx=5, pady=5)
        self.local.grid(row=0, column=0, sticky='ew')
        self.local.columnconfigure(0, weight=1)
        self.treeLocal = ttk.Treeview(self.local)
        self.treeLocal.bind('<Double-Button-1>', self.selectItemLocal)
        self.treeLocal.grid(row=0, column=0, sticky='ew')

        self.scrollLocal = ttk.Scrollbar(self.local, orient=VERTICAL, command=self.treeLocal.yview)
        self.treeLocal.configure(yscrollcommand=self.scrollLocal.set)
        self.scrollLocal.grid(row=0, column=2,sticky='ns', in_=self.local)

        col = ["Type de fichier", "Taille du fichier"]
        self.treeLocal["columns"]=list(range(len(col)))
        for c,i in enumerate(col):
            self.treeLocal.column(str(c))
            self.treeLocal.heading(str(c), text=i)
        self.treeLocal.heading('#0', text='Nom de fichier')
        self.updateParcourirLocal()

        # Frame 2 -- Parcourir : Distant --
        self.distant = LabelFrame(self.parcourir, text="Distant", padx=5, pady=5)
        self.distant.grid(row=0, column=1, sticky='we')
        self.distant.columnconfigure(0, weight=1)
        self.treeDistant = ttk.Treeview(self.distant)
        self.treeDistant.bind('<Double-Button-1>', self.selectItemDistant)
        self.treeDistant.grid(row=0, column=0, sticky='ew')

        self.scrollDistant = ttk.Scrollbar(self.distant, orient=VERTICAL, command=self.treeDistant.yview)
        self.treeDistant.configure(yscrollcommand=self.scrollDistant.set)
        self.scrollDistant.grid(row=0, column=2,sticky='ns', in_=self.distant)

        col = ["Type de fichier", "Taille du fichier"]
        self.treeDistant["columns"]=list(range(len(col)))
        for c,i in enumerate(col):
            self.treeDistant.column(str(c))
            self.treeDistant.heading(str(c), text=i)
        self.treeDistant.heading('#0', text='Nom de fichier')

        # Frame 3 -- Statut --
        self.statut = LabelFrame(self.root, text="Statut", padx=5, pady=5)
        self.statut.grid(row=3, column=0, sticky='ew')
        self.statut.rowconfigure(0, weight=1)
        self.statut.columnconfigure(0, weight=1)
        self.treeStatut = ttk.Treeview(self.statut)
        self.treeStatut.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky='ew')
        self.treeStatut['show'] = 'headings' # Supprimer première colonne vide

        self.scrollStatut = ttk.Scrollbar(self.statut, orient=VERTICAL, command=self.treeStatut.yview)
        self.treeStatut.configure(yscrollcommand=self.scrollStatut.set)
        self.scrollStatut.grid(row=0, column=2,sticky='ns', in_=self.statut)

        col =["Fichier", "Statut", "Taille", "Restant", "Progression"]
        self.treeStatut["columns"]=list(range(len(col)))
        for c,i in enumerate(col):
            self.treeStatut.column(str(c))
            self.treeStatut.heading(str(c), text=i)

    def ajouterRepertoire(self):
        'Menu : Ajouter un répertoire à parcourir localement'
        rep = filedialog.askdirectory(initialdir = ".")
        if rep:
            chemin = os.path.abspath(rep)
            self.repertoireLocal.append(chemin)
            if not self.treeLocal.exists(chemin):
                parent = self.treeLocal.insert('', 'end', chemin, text=chemin, open=True, tags=('dossier', chemin))
                self.parcourirLocal(parent, chemin)

    def repertoireTelechargement(self):
        'Menu : Répertoire de téléchargement des fichiers'
        rep = filedialog.askdirectory(initialdir = ".")
        if rep:
            self.cheminTelechargement = os.path.abspath(rep)

    def aide(self):
        'Menu : A propops'
        apropos = Tk()
        texte1 = "Logiciel de transfère de fichiers se connectant à un serveur socket. " 
        texte2 = "Vous pouvez ajouter des répertoires locaux en les ajoutant via le menu 'Fichier'. "
        texte3 = "De plus vous pouvez uploader un répertoire entier mais ne pouvez en télécharger un."
        msg = Message(apropos, text = texte1+texte2+texte3, width=550)
        msg.config(font=("",12))
        msg.grid(row=0, column=0)
        apropos.mainloop()

    def estImage(self, f):
        'Est image, renvois true ou false'
        extensions = ['.jpg', '.png', '.gif', '.bmp', '.svg', '.tif', '.ico']
        return any(f.lower().endswith(ext) for ext in extensions)

    def updateParcourirLocal(self):
        'Met à jours le parcours local : Arborescence local'
        for chemin in self.repertoireLocal:
            if self.treeLocal.exists(chemin):
                self.treeLocal.delete(chemin)
            parent = self.treeLocal.insert('', 'end', chemin, text=chemin, open=True, tags=('dossier', chemin))
            self.parcourirLocal(parent, chemin)

    def parcourirLocal(self, parent, chemin):
        'Affiche le parcours local : Fichiers et dossiers et leurs valeurs'
        for nom in os.listdir(chemin): # Boucle sur les fichiers du chemin Local
            if not nom.startswith('.'): # Ne pas gérer les fichiers cachés
                cheminFichier = os.path.join(chemin, nom)
                taille = self.conversion(os.path.getsize(cheminFichier))
                if not os.path.isdir(cheminFichier):
                    if self.estImage(cheminFichier):
                        elem = self.treeLocal.insert(parent, 'end', cheminFichier, text=nom, values=('Fichier', taille), open=False, image=self.imageImg, tags=('fichier', cheminFichier))
                    else:
                        elem = self.treeLocal.insert(parent, 'end', cheminFichier, text=nom, values=('Fichier', taille), open=False, image=self.fichierImg, tags=('fichier', cheminFichier))
                if os.path.isdir(cheminFichier):
                    elem = self.treeLocal.insert(parent, 'end', cheminFichier, text=nom, values=('Dossier'), open=False, image=self.dossierImg, tags=('dossier', cheminFichier))
                    self.parcourirLocal(elem, cheminFichier)

    def parcourirDistant(self, chemin):
        'Affiche le parcours Distant : Fichiers et dossiers et leurs valeurs'
        if self.treeDistant.exists('Distant'):
            self.treeDistant.delete('Distant')
        parent = self.treeDistant.insert('', 'end','Distant', text='Distant', open=True, tags=('dossier'))
        for elem in chemin:
            if 'Repertoire' in elem:
                racine =os.path.basename(elem['Repertoire'])
            elif elem['type'] == 'dossier':
                rep = os.path.basename(os.path.dirname(elem['chemin']))
                if rep == racine:
                    rep = parent
                self.treeDistant.insert(rep, 'end', elem['nom'], text=elem['nom'], values=('Dossier'), open=False, image=self.dossierImg, tags=('dossier', elem['chemin']))
            elif elem['type'] == 'fichier':
                fImage = self.fichierImg
                if self.estImage(elem['nom']):
                    fImage = self.imageImg
                dossier = elem['dossier']
                if elem['dossier'] == '.':
                    dossier = parent
                self.treeDistant.insert(dossier, 'end', text=elem['nom'], values=('Fichier', elem['taille']), open=False, image=fImage, tags=('fichier', elem['chemin']))

    def affichageLog(self, message, niveau=''):
        'Affiche les logs dans la fenêtre de logs'
        date = time.strftime("%m/%d/%Y-%H:%M:%S")
        self.scroll.insert('end', '{} - {} \n'.format(date, message), niveau)

    def conversion(self, nbr):
        'Convertis les valeurs dans leurs unités respectives'
        unites = ['Octets', 'Ko', 'Mo', 'Go', 'To'];
        if (nbr == 0):
            return '0 Octets'
        i = int(math.floor(math.log(nbr) / math.log(1000)))
        valeur = round(nbr / math.pow(1000, i), 2)
        return '{} {}'.format(valeur, unites[i]) 

    def connexion(self):
        'Récupères les entrées et les envois au serveur'
        identifiant, motdepasse, serveur, port  = self.identifiantEntry.get(), self.motdepasseEntry.get(),\
                                                  self.serveurEntry.get(), self.portEntry.get() 
        if identifiant and motdepasse and serveur and port: # S'assurer de recevoir toutes les entrées
            if port.isdigit(): # S'assurere que le port est un nombre
                self.ids = {'Identifiant': identifiant, 'Motdepasse' : motdepasse}
                self.affichageLog('Connexion en cours')
                if self.lancer:
                    self.affichageLog('Déconnexion du serveur', 'erreur')
                    self.lancer = False
                self.thread = Thread(target=self.connexionSocket).start() # Lance le thread gérant la connexion
            else:
                messagebox.showwarning("Erreur", "Port invalide", detail="Veuillez changer de port")
        else:
            messagebox.showwarning("Erreur", "Champs vides", detail="Veuillez remplir les champs")

    def selectItemLocal(self, event):
        'Selectionner un item dans le parcours local'
        selection = self.treeLocal.focus()
        if not self.treeStatut.exists(os.path.basename(self.treeLocal.item(selection)['tags'][1])):
            self.action(self.treeLocal.item(selection), 'envoyer') # Appel la fonction action qui va traité l'item

    def selectItemDistant(self, event):
        'Selectionner un item dans le parcours distant'
        selection = self.treeDistant.focus()
        self.action(self.treeDistant.item(selection), 'recevoir') # Appel la fonction action qui va traité l'item

    def action(self, f, t):
        "Action de selection de l'item, envois l'item en queue"
        if self.lancer:
            if f['text'] == 'Distant': # Gestion du téléchargement de dossier distant
                messagebox.showinfo("Erreur", "Download dossier", detail="En construction!") # Non fait
            else:
                types, chemin = f['tags'][0], f['tags'][1]
                if t =='envoyer': # Si fichier est à uploader
                    if types == 'dossier':
                        for i in os.listdir(chemin): # Boucle si c'est un dossier afin d'avoir les fichiers et sous dossiers
                            cheminFichier = os.path.join(chemin, i)
                            estDossier = os.path.isdir(cheminFichier)
                            if not estDossier:
                                if os.path.getsize(cheminFichier) > 0: # Exclure fichier vide
                                    self.enQueue('Envois', cheminFichier) # Envois à la fonction queue afin de le mettre en file d'attente
                            if estDossier:
                                self.action(self.treeLocal.item(cheminFichier), 'envoyer')
                    elif types == 'fichier':
                        if os.path.getsize(chemin) > 0: # Exclure fichier vide
                            self.enQueue('Envois', chemin) # Envois à la fonction queue afin de le mettre en file d'attente
                    else:
                        print('Erreur')
                        sys.exit()
                elif t == 'recevoir': # Si fichier est à télécharger
                    if f['tags'][0] == 'fichier':
                        if f['values'][1] == '0 Octets': # Exclure fichier vide
                            messagebox.showinfo("Erreur", "Fichier invalide")
                        else:
                            self.enQueue('Recevoir', f) # Envois à la fonction queue afin de le mettre en file d'attente
                    else:
                        messagebox.showinfo("Erreur", "Download dossier", detail="En construction!")

    def enQueue(self, statut, fChemin):
        "Met l'item en queue"
        if statut =='Envois': # Fichier à uploader
            if not self.treeStatut.exists(os.path.basename(fChemin)):
                fNom, fTaille = os.path.basename(fChemin), os.path.getsize(fChemin) # Nom et taille du fichier
                fMd5 = hashlib.md5(open(fChemin,'rb').read()).hexdigest() # Hash du fichier
                item = {'Statut': statut, 'Nom': fNom, 'Taille' : fTaille, 'Chemin' : fChemin, 'Hash': fMd5}
                self.treeStatut.insert("", 'end', fNom, values=(fNom, 'En attente', self.conversion(fTaille), self.conversion(fTaille), '0%')) # Met le fichier dans le Statut
                self.queue.put(item) # Met l'item dans la file
        elif statut =='Recevoir': # Fichier à télécharger
            if not self.treeStatut.exists(fChemin['text']):
                fNom, fChemin, fType = fChemin['text'], fChemin['tags'][1], fChemin['tags'][0] # Nom, chemin, taille du fichier
                item = {'Statut': statut, 'Nom': fNom, 'Chemin' : fChemin, 'Type': fType}       
                self.treeStatut.insert("", 'end', fNom, values=(fNom, 'En attente', '/', '/', '0%')) # Met le fichier dans le Statut
                self.queue.put(item) # Met l'item dans la file

    def connexionSocket(self):
        "Thread de connexion socket, upload et download"
        self.connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Initialisation de la connexion
        host, port = self.serveurEntry.get(), int(self.portEntry.get()) # Recevoir les entrées ports et hote
        try:
            self.connexion.connect((host, port)) # Connexion au serveur
        except socket.error:
            self.affichageLog('La connexion a échoué.', 'erreur')
            sys.exit()
        self.connexion.send('connexion'.encode('Utf-8')) # Envois au serveur 'Connexion' afin de préparer les envois des identifiants
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'ok':
            self.envoyer(self.ids) # Envois des identifiants
        else:
            print(reponse)
            self.affichageLog('Le serveur ne répond pas (1).', 'erreur')
            sys.exit()
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'Identifiant incorrect':
            self.affichageLog('Identifiant incorrect', 'erreur')
        elif reponse == 'Mot de passe incorrect':
            self.affichageLog('Mot de passe incorrect', 'erreur')
        elif reponse == 'Connexion réussie':
            self.affichageLog('Connexion établie avec le serveur.', 'réussie')
            self.lancer = True # Connecter au serveur 
            reponse = self.recevoir()
            self.parcourirDistant(reponse) # Reception de l'aborescence distante des fichiers du serveur et gestion de ceux ci
            self.envois = False
            while self.run and self.lancer or self.envois: # Boucle d'attente d'action
                while not self.queue.empty(): # Boucle tant que la file d'attente n'est pas vide
                    self.envois = True
                    fichier = self.queue.get() # Reception du premier item de la liste
                    if fichier['Statut'] == 'Envois': # L'item est à envoyer (uploadé)
                        self.envoyerFichier(fichier) # Envois du fichier au serveur 
                        self.connexion.send('ok'.encode('Utf-8'))
                        reponse = self.recevoir() # Reception de l'aborescence des fichiers du serveur
                        self.parcourirDistant(reponse) # Met à jours l'arborescence des fichiers
                        time.sleep(1)
                        self.envois = False
                    elif fichier['Statut'] == 'Recevoir': # L'item est à recevoir (téléchargé)
                        self.recevoirFichier(fichier) # Reception du fichier 
                        self.updateParcourirLocal() # Met à jours l'arborescence local
                        time.sleep(1)
                        self.envois = False
            self.connexion.send('quit'.encode('Utf-8'))
            sys.exit()
        else:
            print(reponse)
            self.affichageLog('Le serveur ne répond pas (2).', 'erreur')
            sys.exit()

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
            sys.exit()

    def recevoir(self):
        "Reception d'un message Pickle"
        messageHeader = self.connexion.recv(self.tailleHeader)
        messageHeader = int(messageHeader.decode('Utf-8'))
        self.connexion.send('recu'.encode('Utf-8'))
        message = self.connexion.recv(messageHeader)
        return pickle.loads(message)

    def envoyerFichier(self, fichier):
        'Upload du fichier et gestion des statuts'
        self.connexion.send('envois'.encode('Utf-8')) # Envois au serveur qu'on souhaite uploader un fichier
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'ok':
            self.affichageLog('Upload du fichier: {}'.format(fichier['Nom']))
            message = {'Nom': fichier['Nom'], 'Taille' : fichier['Taille'], 'Hash': fichier['Hash']}
            self.envoyer(message)
            reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
            if reponse == 'ok':
                with open(fichier['Chemin'], 'rb') as f: # Ouvre le fichier afin de le lire et d'envoyer les données
                    count, offset, tmpTaille = 200000, 0, fichier['Taille']
                    if tmpTaille > 0:
                        while tmpTaille > 0: # Boucle tant que le fichier uploadé est plus grand que 0
                            data = self.connexion.sendfile(f, offset, count) # Envois du fichier 
                            offset += data
                            tmpTaille -= data # Pour l'affichage de la progression décrémente la taille
                            val = round((offset*100)/fichier['Taille']) # % de l'upload
                            self.treeStatut.item(fichier['Nom'], values=(fichier['Nom'], 'Upload', self.conversion(fichier['Taille']), self.conversion(tmpTaille), str(val)+'%')) # Affichage de l'item dans la frame statut 
                        self.treeStatut.item(fichier['Nom'], values=(fichier['Nom'], 'Upload Terminé', self.conversion(fichier['Taille']), self.conversion(tmpTaille), str(val)+'%'))
                    else:
                        self.affichageLog('Fichier de taille 0', 'erreur')
                        sys.exit()
                reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8') # Reception de la vérification du Hash
                if reponse == 'Hash correspond':
                    self.affichageLog('Upload terminé: {}.'.format(fichier['Nom']), 'réussie')
                elif reponse == 'Hash ne correspond pas':
                    self.affichageLog('Upload terminé: {} mais hash ne correspond pas.'.format(fichier['Nom']), 'erreur')
                else:
                    print(reponse)
                    self.affichageLog('Le serveur ne répond pas (5).', 'erreur')
            else:
                self.affichageLog('Le serveur ne répond pas (4).', 'erreur')
        else:
            self.affichageLog('Le serveur ne répond pas (3).', 'erreur')

    def recevoirFichier(self, fichier):
        'Téléchargement du fichier et gestion des statuts'
        self.connexion.send('recevoir'.encode('Utf-8')) # Envois au serveur qu'on souhaite télécharger
        reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
        if reponse == 'ok':
            message = {'Nom': fichier['Nom'], 'Chemin': fichier['Chemin'], 'Type': fichier['Type']}
            self.envoyer(message) # Envois du fichier au serveur qu'on veut télécharger
            reponse = self.connexion.recv(self.tailleHeader).decode('Utf-8')
            if reponse == 'ok':
                reponse = self.recevoir()
                fNom, fTaille, tmpTaille, fHash = reponse['Nom'], self.conversion(reponse['Taille']), reponse['Taille'], reponse['Hash']
                self.affichageLog('Download du fichier: {}'.format(fNom))
                self.connexion.send('ok'.encode('Utf-8'))
                with open(self.cheminTelechargement+'/'+fNom, 'wb') as f: # Ouvre le fichier afin d'y écrire les données recues
                    dataTotal = b''
                    dl=0
                    lecture = True # Commencement de la lecture et écriture du fichier
                    while reponse['Taille'] > len(dataTotal): # Boucle tant que le fichier téléchargé est moins grand que la taille recue
                        data = self.connexion.recv(200000) # Recois 
                        if not data:
                            break
                        dataTotal += data
                        tmpTaille -= len(data) # Pour l'affichage de la progression décrémente la taille
                        dl = len(dataTotal)
                        val = round((dl*100)/int(reponse['Taille'])) # % de téléchargement
                        f.write(data)
                        self.treeStatut.item(fNom, values=(fNom, 'Download', fTaille, self.conversion(tmpTaille), str(val)+'%')) # Affichage dans le statut de l'item
                    self.treeStatut.item(fNom, values=(fNom, 'Download Terminé', fTaille, self.conversion(tmpTaille), str(val)+'%'))
                    lecture = False # Fin de la lecture et écriture du fichier
                if lecture == False:
                    fMd5Telecharger = hashlib.md5(open(self.cheminTelechargement+'/'+fNom,'rb').read()).hexdigest() # Hash du fichier recu
                    if fMd5Telecharger == fHash: # Vérification du Hash recu et celui téléchargé
                        self.affichageLog('Download terminé: {}.'.format(fNom), 'réussie')
                        self.affichageLog('Hash ok {}.'.format(fMd5Telecharger), 'réussie')
                        self.connexion.send('Hash correspond'.encode('Utf-8'))
                    else:
                        self.affichageLog('Download terminé mais hash {} =/ {} ne correspond pas.'.format(fMd5Telecharger, fHash), 'erreur')
                        self.connexion.send('Hash ne correspond pas'.encode('Utf-8'))
                else:
                    self.affichageLog('Problème détecté', 'erreur')
                    sys.exit()

if __name__ == '__main__':
    from tkinter import *
    f = App()
