-- MySQL dump 10.13  Distrib 8.0.33, for Win64 (x86_64)
--
-- Host: localhost    Database: marking_system
-- ------------------------------------------------------
-- Server version	8.0.33

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `activation_codes`
--

DROP TABLE IF EXISTS `activation_codes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `activation_codes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `max_activations` int DEFAULT '3',
  `current_activations` int DEFAULT '0',
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NULL DEFAULT NULL,
  `status` enum('active','inactive','expired') COLLATE utf8mb4_unicode_ci DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `activation_codes_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activation_codes`
--

LOCK TABLES `activation_codes` WRITE;
/*!40000 ALTER TABLE `activation_codes` DISABLE KEYS */;
INSERT INTO `activation_codes` VALUES (1,'hS58-WhOV-gWCv-W2pL',3,1,2,'2025-07-07 07:43:35',NULL,'active'),(2,'zgUR-e31L-lYK2-2ZJr',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(3,'RzFY-t6QC-qduG-Pbu8',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(4,'kzX9-wnXb-M0p0-xt2v',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(5,'O777-tDAd-hSyW-fRDg',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(6,'xU5K-th7b-RSYo-HvEB',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(7,'k41B-tD70-OWBj-hUIh',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(8,'RyOL-6Afc-Sy9q-fKq4',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(9,'d4BV-p77i-uhT6-75W7',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(10,'fPg1-6YLE-I82l-Uft1',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(11,'WFpk-UqCV-gTw2-dRB8',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(12,'W3gJ-Zxah-HRno-VjS8',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(13,'Md4Y-3nhx-wMy1-nrEu',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(14,'lscY-d05Z-hslX-G9t5',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(15,'OorO-7fo7-5ZBX-bhMK',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(16,'pmpO-2wd9-w4cn-1TK3',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(17,'iIF6-xE27-qHbz-Y8BE',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(18,'yw65-nf0L-FR58-Eqd1',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(19,'5Whf-68wd-VAz9-3AJw',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(20,'uPpN-Nu1X-igGW-DdH2',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(21,'SLBV-6sJN-KHQT-owoK',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(22,'cRNl-CW8P-Wsfc-YWAC',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(23,'Obr4-c0wF-GEwX-Sxpq',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(24,'n80E-BL5r-hyGU-NpDt',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(25,'kPlA-ZgML-Yku1-fLSD',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(26,'0lXh-DNI7-gptR-e248',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(27,'9M2V-x91q-KEDh-ZYsq',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(28,'oq8c-MI66-CDKq-ZxoI',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(29,'jM6o-CTPB-Firp-tD2w',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(30,'9D9y-CFyK-aSl2-P5Ub',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(31,'yVvj-8WH7-jOYO-KsmR',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(32,'aSoM-u9ri-6uNQ-7qfW',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(33,'heUN-WMFX-658J-nQJY',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(34,'HBWI-OQLF-6Fun-3Lzw',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(35,'81m9-NdFQ-9ho6-Za9G',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(36,'ZZMa-jfE8-qSZ8-5Trb',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(37,'cLnJ-9CSP-VRia-1EDx',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(38,'AcFG-WXW0-22I0-6TO9',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(39,'eQWn-BXHW-86Aq-DkM2',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(40,'3Vs7-jUvz-Rbyd-N0lJ',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(41,'nUPY-kad2-bm8h-qoSF',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(42,'L6hv-I97m-w5WR-N5Ul',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(43,'pLIg-pK2S-34xK-dUzY',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(44,'FX4z-kdx4-IEVr-4Xgx',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(45,'VcwB-7kYB-yBiv-kjgA',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(46,'DRLq-tD1I-chsd-8hLt',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(47,'2epV-clho-A81H-8YgG',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(48,'3pcW-lNYT-eMLv-KWBM',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(49,'qi69-TKWr-qbXO-yXSz',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(50,'YwFb-v9on-jEwu-lLu9',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(51,'vQVw-M4y6-xiOg-hEGK',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(52,'Ot9d-2D0m-rPmi-h8OE',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(53,'UAZ0-FJ6U-T9PP-270e',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(54,'3apn-Vmxv-S28W-Ap8m',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(55,'3NeO-FWw4-GdQD-sZi8',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(56,'DbFr-rzq7-17ZC-wnHI',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(57,'1IPQ-aE2F-CGRR-RPJl',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(58,'jDuP-2NsQ-ZUNK-pyEB',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(59,'qS2o-SW4f-rMHP-9Pyh',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(60,'ehXt-kP5x-iXvQ-F9EC',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(61,'WZ2m-TJGe-slPQ-4nSu',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(62,'lR6u-uPgi-NFjF-pbY2',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(63,'iES4-P04l-zopF-6oG8',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(64,'7ZDO-826h-Hc5A-rib9',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(65,'RzZE-YRU7-fxrR-VZ7R',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(66,'xc9P-xDDs-c9tB-PGXG',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(67,'T5IQ-ccAc-zKcf-YLXc',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(68,'KpC8-EfaK-jh14-mL5H',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(69,'SfKx-ypqL-AYH8-QxQj',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(70,'zObb-GcgI-8gGO-Aa5F',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(71,'Rf7f-TnOi-8nDi-lXjq',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(72,'VRPS-oOsN-0y6s-SzAZ',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(73,'HqR1-3mbP-Tr2E-XmSe',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(74,'9CVy-K9LM-jPSi-mxcU',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(75,'RRjg-U1Oo-doKD-eo9q',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(76,'l4tX-ajQ7-Uo28-HjO1',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(77,'m69E-j4PB-irvB-tV9E',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(78,'pKxE-VfJk-xikX-dHq0',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(79,'0Grb-N2Ym-ndMV-QSBJ',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(80,'MxTF-nd8A-N05N-SQdM',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(81,'HxpM-Zt5z-ialn-jmFN',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(82,'b5ga-wIF4-Kqaq-edi9',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(83,'60AG-AbVQ-r8ul-D5al',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(84,'unNQ-UqQE-e23U-gPcv',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(85,'q6Mu-SFoy-rt3l-Ib2I',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(86,'FRpB-tq3Z-2E2V-JjCg',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(87,'7KNF-GaSj-m5rA-ONt1',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(88,'hrBX-26kT-FGLN-tyCZ',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(89,'RxIE-WAJI-LnaH-46xD',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(90,'8e7G-z2hE-LvRa-GW2B',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(91,'TrAn-2WkU-g8Qm-t9XA',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(92,'kEEm-Rtuc-pw5B-Dj5B',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(93,'KVwV-pXSX-h1hw-oqcN',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(94,'2SaZ-ukWu-nasw-yej7',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(95,'jFQJ-0dVD-vF8x-iIcx',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(96,'Rijo-7SoF-r2xp-cJQK',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(97,'PBS5-vHSI-TKy4-bHhO',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(98,'PGWb-3KXW-QN3Z-tdUF',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(99,'IBsj-kI74-0lQn-LGys',3,0,2,'2025-07-07 07:43:35',NULL,'inactive'),(100,'Ydia-vKDx-Dpr3-Arqo',3,0,2,'2025-07-07 07:43:35',NULL,'inactive');
/*!40000 ALTER TABLE `activation_codes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `activations`
--

DROP TABLE IF EXISTS `activations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `activations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `activation_code_id` int NOT NULL,
  `device_id` int NOT NULL,
  `activation_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expiration_time` timestamp NULL DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `activation_code_id` (`activation_code_id`,`device_id`),
  KEY `device_id` (`device_id`),
  CONSTRAINT `activations_ibfk_1` FOREIGN KEY (`activation_code_id`) REFERENCES `activation_codes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `activations_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activations`
--

LOCK TABLES `activations` WRITE;
/*!40000 ALTER TABLE `activations` DISABLE KEYS */;
INSERT INTO `activations` VALUES (1,1,1,'2025-07-20 12:34:02',NULL,1);
/*!40000 ALTER TABLE `activations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `devices`
--

DROP TABLE IF EXISTS `devices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `devices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `hardware_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `hostname` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `os_info` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_activation_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_verification_time` timestamp NULL DEFAULT NULL,
  `status` enum('active','inactive','blocked') COLLATE utf8mb4_unicode_ci DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `hardware_id` (`hardware_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `devices`
--

LOCK TABLES `devices` WRITE;
/*!40000 ALTER TABLE `devices` DISABLE KEYS */;
INSERT INTO `devices` VALUES (1,'1478a1a18f251a0e7b3a91685c1fd84471ac9b7def26367ae5242d89d69a9cf6',NULL,NULL,'2025-07-07 07:47:01','2025-07-07 07:48:26','active');
/*!40000 ALTER TABLE `devices` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `login_logs`
--

DROP TABLE IF EXISTS `login_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `login_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('success','failed') COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `login_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_logs`
--

LOCK TABLES `login_logs` WRITE;
/*!40000 ALTER TABLE `login_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `login_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_admin` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  `status` enum('active','inactive','suspended') COLLATE utf8mb4_unicode_ci DEFAULT 'active',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (2,'admin','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',NULL,1,'2025-07-07 07:43:35',NULL,'active');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-22 20:26:54
