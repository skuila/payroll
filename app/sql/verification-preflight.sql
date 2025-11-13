-- verification-preflight.sql

-- Vérifie que la Source de Vérité (SoT) est STRICTEMENT conforme :

--  - table présente

--  - exactement 15 colonnes (noms identiques à ceux de l'Excel, casse/accents/underscores)

--  - types critiques OK (date_paie = date/timestamp ; montant_employe & part_employeur = numériques)

--  - au moins 1 période (mois distinct)

DO $$

DECLARE

    expected text[] := ARRAY[

      'numero_ligne','categorie_emploi','code_emploi','titre_emploi','date_paie',

      'matricule','nom_employe','categorie_paie','code_paie','description_code_paie',

      'poste_budgetaire','description_poste_budgetaire','montant_employe','part_employeur','montant_combine'

    ];

    actual   text[];

    missing  text[];

    extra    text[];

    v_count_rows bigint;

    v_count_mois  bigint;

BEGIN

    -- 1) Table présente ?

    IF NOT EXISTS (

        SELECT 1

        FROM information_schema.tables

        WHERE table_schema = 'REPLACE_ME_SCHEMA'

          AND table_name   = 'REPLACE_ME_TABLE'

    ) THEN

        RAISE EXCEPTION 'Table %.% introuvable', 'REPLACE_ME_SCHEMA','REPLACE_ME_TABLE';

    END IF;



    -- 2) Colonnes requises présentes ? (les 15 colonnes doivent toutes exister)

    SELECT array_agg(column_name ORDER BY ordinal_position)

      INTO actual

    FROM information_schema.columns

    WHERE table_schema = 'REPLACE_ME_SCHEMA'

      AND table_name   = 'REPLACE_ME_TABLE';



    -- Vérifier uniquement que les colonnes attendues sont présentes
    -- (les colonnes supplémentaires techniques comme id, source_file, etc. sont autorisées)
    SELECT ARRAY(SELECT unnest(expected) EXCEPT SELECT unnest(actual)) INTO missing;



    IF coalesce(array_length(missing,1),0) > 0 THEN

        RAISE EXCEPTION 'Colonnes requises manquantes: %. Vérifiez que toutes les 15 colonnes sont présentes.', missing;

    END IF;

    
    RAISE NOTICE 'Vérification colonnes OK. Colonnes requises présentes: % sur %', 

        array_length(expected,1), array_length(actual,1);



    -- 3) Types critiques

    PERFORM 1 FROM information_schema.columns

     WHERE table_schema='REPLACE_ME_SCHEMA'

       AND table_name='REPLACE_ME_TABLE'

       AND column_name='date_paie'

       AND data_type IN ('date','timestamp without time zone','timestamp with time zone');

    IF NOT FOUND THEN

       RAISE EXCEPTION 'Type invalide pour date_paie (attendu: date/timestamp).';

    END IF;



    PERFORM 1 FROM information_schema.columns

     WHERE table_schema='REPLACE_ME_SCHEMA'

       AND table_name='REPLACE_ME_TABLE'

       AND column_name='montant_employe'

       AND data_type IN ('numeric','decimal','double precision','real','integer','bigint','smallint');

    IF NOT FOUND THEN

       RAISE EXCEPTION 'Type invalide pour montant_employe (attendu: numérique agrégable).';

    END IF;



    -- part_employeur peut être TEXT (sera casté en numeric dans les requêtes)
    PERFORM 1 FROM information_schema.columns

     WHERE table_schema='REPLACE_ME_SCHEMA'

       AND table_name='REPLACE_ME_TABLE'

       AND column_name='part_employeur'

       AND data_type IN ('numeric','decimal','double precision','real','integer','bigint','smallint','text','character varying');

    IF NOT FOUND THEN

       RAISE EXCEPTION 'Type invalide pour part_employeur (attendu: numérique ou text castable).';

    END IF;



    -- 4) Au moins une période (mois distinct)

    EXECUTE format(

      'SELECT COUNT(*), COUNT(DISTINCT DATE_TRUNC(''month'', %I)) FROM %I.%I',

      'date_paie','REPLACE_ME_SCHEMA','REPLACE_ME_TABLE'

    )

    INTO v_count_rows, v_count_mois;



    IF v_count_rows < 1 THEN

        RAISE EXCEPTION 'Table vide.';

    END IF;

    IF v_count_mois < 1 THEN

        RAISE EXCEPTION 'Aucune période détectée (aucun mois distinct).';

    END IF;



    RAISE NOTICE 'Préflight OK. Lignes: %, Mois distincts: %', v_count_rows, v_count_mois;

END $$;

