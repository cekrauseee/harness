---
description: >-
  Contexte externe par projet et procédures de développement ciblées pour les agents.
metaDescription: >-
  Harness conserve les connaissances utiles et le contexte de reprise dans des fichiers Markdown locaux, hors du dépôt. Dix skills indépendants couvrent la planification, la délibération entre pairs, la réalisation, la revue et les opérations Git sur Codex et Claude Code.
summary: >-
  Harness fournit à chaque projet un environnement externe partagé par ses worktrees Git. Dix skills indépendants couvrent le contexte, la planification modulaire, les transmissions, la coordination des agents, la délibération entre pairs et les procédures de développement sur Codex et Claude Code, avec un seul fichier d’instructions partagé. Ces procédures guident les agents vers le contexte pertinent pour chaque tâche.
highlights:
  - un environnement par projet et ses worktrees
  - dix skills indépendants pour Codex et Claude Code
  - contexte conservé dans des fichiers et consulté au besoin
  - mises à jour atomiques de Markdown sans réservation de fichiers
---

Harness fournit à chaque projet un environnement externe partagé par ses worktrees Git. Dix skills indépendants couvrent le contexte, la planification modulaire, les transmissions, la coordination des agents, la délibération entre pairs et les procédures de développement sur Codex et Claude Code, avec un seul fichier d’instructions partagé. Ces procédures guident les agents vers le contexte pertinent pour chaque tâche.

## Le contexte du projet en dehors du dépôt

Chaque dépôt ou monorepo possède un environnement local. Son index succinct aide les agents à découvrir les contraintes applicables et à trouver le contexte pertinent. Les connaissances utiles résident dans des fichiers Markdown organisés par sujet. Les plans temporaires, la configuration des agents et le contexte de reprise existent uniquement au besoin ; les petites modifications individuelles ne nécessitent aucun dossier de travail.

## Des procédures ciblées et un contexte délimité

Les plans globaux sont modulaires quel que soit le nombre d’agents. Les équipes de réalisation et de revue peuvent référencer les mêmes livrables tout en conservant un contexte d’exécution distinct. Une transmission transfère la responsabilité par des références aux fichiers canoniques, sans recopier les conversations.

Sur demande, la délibération entre pairs réunit les agents pour élaborer une analyse, une décision ou une proposition. Les participants contribuent et questionnent les idées sur un pied d’égalité, affinent une synthèse commune et préservent les désaccords importants. La coordination organise les échanges sans déterminer quel point de vue doit prévaloir.

## Deux hôtes, un seul jeu d’instructions

Un seul fichier d’instructions sert Codex et Claude Code : Codex le lit directement, Claude Code l’importe, et chaque hôte applique une courte section qui lui est propre. La mécanique propre à chaque hôte, comme la mémoire et les worktrees gérées, relève du plugin ; la personne ne définit que des choix pratiques tels que la langue, les conventions de branches et la politique de tests.

## Worktrees et persistance sûre

Les worktrees créées par Harness résident dans l’environnement du projet ; celles gérées par l’hôte sont acceptées là où elles se trouvent. Les agents qui collaborent au sein d’une équipe peuvent alterner les écritures ; les équipes indépendantes utilisent des copies de travail distinctes. L’utilitaire Python protège les mises à jour Markdown contre l’écrasement de modifications intervenues depuis la lecture.

Une fois le travail terminé, les connaissances utiles sont consolidées et les livrables à conserver sont préservés avec des références actualisées avant le déplacement du contexte temporaire vers la corbeille de l’environnement, que la personne vide quand elle le souhaite. Les éléments encore nécessaires à une autre équipe ou à une transmission en attente restent disponibles. Le retrait d’une worktree est une décision séparée.
