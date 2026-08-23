-- BEGENIDE BASLIK DA SAKLANIYOR.
--
-- "Begendiklerim" listesi yalnizca yol tutsaydi panelde
-- "/haber/tcmb-altin-cinsinden-fiziki..." gibi adresler gorunurdu.
-- Basligi uretim aninda cozmek icin sitenin tamamini sorgulamak
-- gerekirdi; oysa okur begenirken baslik zaten ekranda.
--
-- Baslik BEGENI ANINDAKI halidir ve sonradan degisirse guncellenmez.
-- Bu bilincli: liste okurun o gun ne begendigini gosteriyor.
ALTER TABLE begeni ADD COLUMN baslik TEXT;
