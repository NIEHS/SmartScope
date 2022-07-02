-- MariaDB dump 10.19  Distrib 10.5.16-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: smartscope
-- ------------------------------------------------------
-- Server version	10.5.16-MariaDB-1:10.5.16+maria~focal

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `atlasmodel`
--

DROP TABLE IF EXISTS `atlasmodel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `atlasmodel` (
  `atlas_id` varchar(30) NOT NULL,
  `name` varchar(100) NOT NULL,
  `pixel_size` double DEFAULT NULL,
  `binning_factor` double DEFAULT NULL,
  `shape_x` int(11) DEFAULT NULL,
  `shape_y` int(11) DEFAULT NULL,
  `stage_z` double DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `completion_time` datetime(6) DEFAULT NULL,
  `grid_id_id` varchar(30) NOT NULL,
  PRIMARY KEY (`atlas_id`),
  UNIQUE KEY `atlasmodel_grid_id_id_name_4486e537_uniq` (`grid_id_id`,`name`),
  CONSTRAINT `atlasmodel_grid_id_id_c1918cd9_fk_autoloadergrid_grid_id` FOREIGN KEY (`grid_id_id`) REFERENCES `autoloadergrid` (`grid_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `atlasmodel`
--

LOCK TABLES `atlasmodel` WRITE;
/*!40000 ALTER TABLE `atlasmodel` DISABLE KEYS */;
/*!40000 ALTER TABLE `atlasmodel` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
INSERT INTO `auth_group` VALUES (15,'testing');
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add Token',7,'add_token'),(26,'Can change Token',7,'change_token'),(27,'Can delete Token',7,'delete_token'),(28,'Can view Token',7,'view_token'),(29,'Can add token',8,'add_tokenproxy'),(30,'Can change token',8,'change_tokenproxy'),(31,'Can delete token',8,'delete_tokenproxy'),(32,'Can view token',8,'view_tokenproxy');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=57 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (56,'pbkdf2_sha256$216000$rvBPT3bYjHj3$1G6/eYz68A83ez28r2OT37sRSfMlrcjTid0t02Ic1QY=','2022-05-27 13:08:17.059077',1,'admin','','','',1,1,'2022-05-27 13:07:14.000000');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user_groups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `authtoken_token`
--

DROP TABLE IF EXISTS `authtoken_token`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `authtoken_token` (
  `key` varchar(40) NOT NULL,
  `created` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`key`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `authtoken_token_user_id_35299eff_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `authtoken_token`
--

LOCK TABLES `authtoken_token` WRITE;
/*!40000 ALTER TABLE `authtoken_token` DISABLE KEYS */;
/*!40000 ALTER TABLE `authtoken_token` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `autoloadergrid`
--

DROP TABLE IF EXISTS `autoloadergrid`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `autoloadergrid` (
  `position` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `grid_id` varchar(30) NOT NULL,
  `hole_angle` double DEFAULT NULL,
  `mesh_angle` double DEFAULT NULL,
  `quality` varchar(10) DEFAULT NULL,
  `notes` varchar(10000) DEFAULT NULL,
  `status` varchar(10) DEFAULT NULL,
  `start_time` datetime(6) DEFAULT NULL,
  `last_update` datetime(6) DEFAULT NULL,
  `holeType_id` varchar(100) DEFAULT NULL,
  `meshMaterial_id` varchar(100) DEFAULT NULL,
  `meshSize_id` varchar(100) DEFAULT NULL,
  `params_id_id` varchar(30) DEFAULT NULL,
  `session_id_id` varchar(30) NOT NULL,
  PRIMARY KEY (`grid_id`),
  UNIQUE KEY `autoloadergrid_position_name_session_id_id_9454ae39_uniq` (`position`,`name`,`session_id_id`),
  KEY `autoloadergrid_holeType_id_930f6be8_fk_holetype_name` (`holeType_id`),
  KEY `autoloadergrid_meshMaterial_id_bcb65b9e_fk_meshmaterial_name` (`meshMaterial_id`),
  KEY `autoloadergrid_meshSize_id_da6200b1_fk_meshsize_name` (`meshSize_id`),
  KEY `autoloadergrid_params_id_id_abb5e2f8_fk_gridcolle` (`params_id_id`),
  KEY `autoloadergrid_session_id_id_4389af90_fk_screening` (`session_id_id`),
  CONSTRAINT `autoloadergrid_holeType_id_930f6be8_fk_holetype_name` FOREIGN KEY (`holeType_id`) REFERENCES `holetype` (`name`),
  CONSTRAINT `autoloadergrid_meshMaterial_id_bcb65b9e_fk_meshmaterial_name` FOREIGN KEY (`meshMaterial_id`) REFERENCES `meshmaterial` (`name`),
  CONSTRAINT `autoloadergrid_meshSize_id_da6200b1_fk_meshsize_name` FOREIGN KEY (`meshSize_id`) REFERENCES `meshsize` (`name`),
  CONSTRAINT `autoloadergrid_params_id_id_abb5e2f8_fk_gridcolle` FOREIGN KEY (`params_id_id`) REFERENCES `gridcollectionparams` (`params_id`),
  CONSTRAINT `autoloadergrid_session_id_id_4389af90_fk_screening` FOREIGN KEY (`session_id_id`) REFERENCES `screeningsession` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `autoloadergrid`
--

LOCK TABLES `autoloadergrid` WRITE;
/*!40000 ALTER TABLE `autoloadergrid` DISABLE KEYS */;
/*!40000 ALTER TABLE `autoloadergrid` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `changelog`
--

DROP TABLE IF EXISTS `changelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `changelog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `table_name` varchar(60) NOT NULL,
  `line_id` varchar(30) NOT NULL,
  `column_name` varchar(20) NOT NULL,
  `initial_value` longblob NOT NULL,
  `new_value` longblob NOT NULL,
  `date` datetime(6) NOT NULL,
  `grid_id_id` varchar(30) NOT NULL,
  `user_id` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `changelog_grid_id_id_de6bf00a_fk_autoloadergrid_grid_id` (`grid_id_id`),
  KEY `changelog_user_id_81dee4a9_fk_auth_user_username` (`user_id`),
  CONSTRAINT `changelog_grid_id_id_de6bf00a_fk_autoloadergrid_grid_id` FOREIGN KEY (`grid_id_id`) REFERENCES `autoloadergrid` (`grid_id`),
  CONSTRAINT `changelog_user_id_81dee4a9_fk_auth_user_username` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=1572 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `changelog`
--

LOCK TABLES `changelog` WRITE;
/*!40000 ALTER TABLE `changelog` DISABLE KEYS */;
/*!40000 ALTER TABLE `changelog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `classifier`
--

DROP TABLE IF EXISTS `classifier`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `classifier` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `object_id` varchar(30) NOT NULL,
  `method_name` varchar(50) DEFAULT NULL,
  `label` varchar(30) DEFAULT NULL,
  `content_type_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `classifier_content_type_id_c177300c_fk_django_content_type_id` (`content_type_id`),
  CONSTRAINT `classifier_content_type_id_c177300c_fk_django_content_type_id` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9218 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `classifier`
--

LOCK TABLES `classifier` WRITE;
/*!40000 ALTER TABLE `classifier` DISABLE KEYS */;
/*!40000 ALTER TABLE `classifier` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detector`
--

DROP TABLE IF EXISTS `detector`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `detector` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `detector_model` varchar(30) NOT NULL,
  `atlas_mag` int(11) NOT NULL,
  `atlas_max_tiles_X` int(11) NOT NULL,
  `atlas_max_tiles_Y` int(11) NOT NULL,
  `spot_size` int(11) DEFAULT NULL,
  `frame_align_cmd` varchar(30) NOT NULL,
  `gain_rot` int(11) DEFAULT NULL,
  `gain_flip` tinyint(1) NOT NULL,
  `energy_filter` tinyint(1) NOT NULL,
  `microscope_id_id` varchar(30) NOT NULL,
  `c2_perc` double NOT NULL,
  PRIMARY KEY (`id`),
  KEY `detector_microscope_id_id_c62bb405_fk_microscope_microscope_id` (`microscope_id_id`),
  CONSTRAINT `detector_microscope_id_id_c62bb405_fk_microscope_microscope_id` FOREIGN KEY (`microscope_id_id`) REFERENCES `microscope` (`microscope_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detector`
--

LOCK TABLES `detector` WRITE;
/*!40000 ALTER TABLE `detector` DISABLE KEYS */;
INSERT INTO `detector` VALUES (3,'test_K2','K2',62,6,6,5,'alignframes',3,1,0,'h0PgRUjUq2K2Cr1CGZJq3q08il8i5n',100);
/*!40000 ALTER TABLE `detector` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=276 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(15,'API','atlasmodel'),(10,'API','detector'),(19,'API','finder'),(18,'API','gridcollectionparams'),(16,'API','holemodel'),(11,'API','holetype'),(12,'API','meshmaterial'),(13,'API','meshsize'),(9,'API','microscope'),(17,'API','screeningsession'),(14,'API','squaremodel'),(3,'auth','group'),(2,'auth','permission'),(4,'auth','user'),(7,'authtoken','token'),(8,'authtoken','tokenproxy'),(5,'contenttypes','contenttype'),(6,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_migrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2022-03-28 19:45:39.604977'),(2,'contenttypes','0002_remove_content_type_name','2022-03-28 19:45:39.871200'),(3,'auth','0001_initial','2022-03-28 19:45:40.690613'),(4,'auth','0002_alter_permission_name_max_length','2022-03-28 19:45:44.021735'),(5,'auth','0003_alter_user_email_max_length','2022-03-28 19:45:44.071631'),(6,'auth','0004_alter_user_username_opts','2022-03-28 19:45:44.090858'),(7,'auth','0005_alter_user_last_login_null','2022-03-28 19:45:44.313585'),(8,'auth','0006_require_contenttypes_0002','2022-03-28 19:45:44.343315'),(9,'auth','0007_alter_validators_add_error_messages','2022-03-28 19:45:44.376690'),(10,'auth','0008_alter_user_username_max_length','2022-03-28 19:45:44.438401'),(11,'auth','0009_alter_user_last_name_max_length','2022-03-28 19:45:44.521934'),(12,'auth','0010_alter_group_name_max_length','2022-03-28 19:45:44.580201'),(13,'auth','0011_update_proxy_permissions','2022-03-28 19:45:44.598903'),(14,'auth','0012_alter_user_first_name_max_length','2022-03-28 19:45:44.671816'),(15,'API','0001_initial','2022-03-28 19:45:49.766699'),(16,'admin','0001_initial','2022-03-28 19:45:55.635521'),(17,'admin','0002_logentry_remove_auto_add','2022-03-28 19:45:56.199706'),(18,'admin','0003_logentry_add_action_flag_choices','2022-03-28 19:45:56.234886'),(19,'authtoken','0001_initial','2022-03-28 19:45:56.442933'),(20,'authtoken','0002_auto_20160226_1747','2022-03-28 19:45:57.490956'),(21,'authtoken','0003_tokenproxy','2022-03-28 19:45:57.512029'),(22,'sessions','0001_initial','2022-03-28 19:45:57.662359'),(23,'API','0002_microscope_scope_path','2022-03-30 14:50:35.954750'),(24,'API','0003_detector_c2_perc','2022-03-30 15:45:54.807446'),(25,'API','0002_auto_20220608_1836','2022-07-02 11:03:11.526775'),(26,'API','0003_remove_holemodel_dist_from_center_and_more','2022-07-02 11:03:11.571192');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `finder`
--

DROP TABLE IF EXISTS `finder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `finder` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `object_id` varchar(30) NOT NULL,
  `method_name` varchar(50) DEFAULT NULL,
  `x` int(11) NOT NULL,
  `y` int(11) NOT NULL,
  `stage_x` double NOT NULL,
  `stage_y` double NOT NULL,
  `stage_z` double DEFAULT NULL,
  `content_type_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `finder_content_type_id_8e30ce07_fk_django_content_type_id` (`content_type_id`),
  CONSTRAINT `finder_content_type_id_8e30ce07_fk_django_content_type_id` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=77221 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `finder`
--

LOCK TABLES `finder` WRITE;
/*!40000 ALTER TABLE `finder` DISABLE KEYS */;
/*!40000 ALTER TABLE `finder` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `gridcollectionparams`
--

DROP TABLE IF EXISTS `gridcollectionparams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gridcollectionparams` (
  `params_id` varchar(30) NOT NULL,
  `atlas_x` int(11) NOT NULL,
  `atlas_y` int(11) NOT NULL,
  `square_x` int(11) NOT NULL,
  `square_y` int(11) NOT NULL,
  `squares_num` int(11) NOT NULL,
  `holes_per_square` int(11) NOT NULL,
  `bis_max_distance` double NOT NULL,
  `min_bis_group_size` int(11) NOT NULL,
  `target_defocus_min` double NOT NULL,
  `target_defocus_max` double NOT NULL,
  `step_defocus` double NOT NULL,
  `drift_crit` double NOT NULL,
  `tilt_angle` double NOT NULL,
  `save_frames` tinyint(1) NOT NULL,
  `zeroloss_delay` int(11) NOT NULL,
  PRIMARY KEY (`params_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `gridcollectionparams`
--

LOCK TABLES `gridcollectionparams` WRITE;
/*!40000 ALTER TABLE `gridcollectionparams` DISABLE KEYS */;
/*!40000 ALTER TABLE `gridcollectionparams` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `highmagmodel`
--

DROP TABLE IF EXISTS `highmagmodel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `highmagmodel` (
  `hm_id` varchar(30) NOT NULL,
  `number` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `pixel_size` double DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `is_x` double DEFAULT NULL,
  `is_y` double DEFAULT NULL,
  `frames` varchar(120) DEFAULT NULL,
  `defocus` double DEFAULT NULL,
  `astig` double DEFAULT NULL,
  `angast` double DEFAULT NULL,
  `ctffit` double DEFAULT NULL,
  `grid_id_id` varchar(30) NOT NULL,
  `hole_id_id` varchar(30) NOT NULL,
  `completion_time` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`hm_id`),
  KEY `highmagmodel_grid_id_id_8f8f1849_fk_autoloadergrid_grid_id` (`grid_id_id`),
  KEY `highmagmodel_hole_id_id_0259a98e_fk_holemodel_hole_id` (`hole_id_id`),
  CONSTRAINT `highmagmodel_grid_id_id_8f8f1849_fk_autoloadergrid_grid_id` FOREIGN KEY (`grid_id_id`) REFERENCES `autoloadergrid` (`grid_id`),
  CONSTRAINT `highmagmodel_hole_id_id_0259a98e_fk_holemodel_hole_id` FOREIGN KEY (`hole_id_id`) REFERENCES `holemodel` (`hole_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `highmagmodel`
--

LOCK TABLES `highmagmodel` WRITE;
/*!40000 ALTER TABLE `highmagmodel` DISABLE KEYS */;
/*!40000 ALTER TABLE `highmagmodel` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `holemodel`
--

DROP TABLE IF EXISTS `holemodel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `holemodel` (
  `name` varchar(100) NOT NULL,
  `number` int(11) NOT NULL,
  `pixel_size` double DEFAULT NULL,
  `shape_x` int(11) DEFAULT NULL,
  `shape_y` int(11) DEFAULT NULL,
  `selected` tinyint(1) NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `completion_time` datetime(6) DEFAULT NULL,
  `hole_id` varchar(30) NOT NULL,
  `radius` int(11) NOT NULL,
  `area` double NOT NULL,
  `bis_group` varchar(30) DEFAULT NULL,
  `bis_type` varchar(30) DEFAULT NULL,
  `grid_id_id` varchar(30) NOT NULL,
  `square_id_id` varchar(30) NOT NULL,
  PRIMARY KEY (`hole_id`),
  UNIQUE KEY `holemodel_name_square_id_id_3d66de91_uniq` (`name`,`square_id_id`),
  KEY `holemodel_grid_id_id_e0af6c4d_fk_autoloadergrid_grid_id` (`grid_id_id`),
  KEY `holemodel_square_id_id_b73a5e24_fk_squaremodel_square_id` (`square_id_id`),
  CONSTRAINT `holemodel_grid_id_id_e0af6c4d_fk_autoloadergrid_grid_id` FOREIGN KEY (`grid_id_id`) REFERENCES `autoloadergrid` (`grid_id`),
  CONSTRAINT `holemodel_square_id_id_b73a5e24_fk_squaremodel_square_id` FOREIGN KEY (`square_id_id`) REFERENCES `squaremodel` (`square_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `holemodel`
--

LOCK TABLES `holemodel` WRITE;
/*!40000 ALTER TABLE `holemodel` DISABLE KEYS */;
/*!40000 ALTER TABLE `holemodel` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `holetype`
--

DROP TABLE IF EXISTS `holetype`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `holetype` (
  `name` varchar(100) NOT NULL,
  `hole_size` double DEFAULT NULL,
  `hole_spacing` double DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `holetype`
--

LOCK TABLES `holetype` WRITE;
/*!40000 ALTER TABLE `holetype` DISABLE KEYS */;
INSERT INTO `holetype` VALUES ('Lacey',NULL,NULL),('MultiA',NULL,NULL),('NegativeStain',NULL,NULL),('R0.6/1',0.6,1),('R1.2/1.3',1.2,1.3),('R2/1',2,1),('R2/2',2,2),('R2/4',2,4);
/*!40000 ALTER TABLE `holetype` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `meshmaterial`
--

DROP TABLE IF EXISTS `meshmaterial`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `meshmaterial` (
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `meshmaterial`
--

LOCK TABLES `meshmaterial` WRITE;
/*!40000 ALTER TABLE `meshmaterial` DISABLE KEYS */;
INSERT INTO `meshmaterial` VALUES ('Carbon'),('Gold');
/*!40000 ALTER TABLE `meshmaterial` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `meshsize`
--

DROP TABLE IF EXISTS `meshsize`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `meshsize` (
  `name` varchar(100) NOT NULL,
  `square_size` int(11) NOT NULL,
  `bar_width` int(11) NOT NULL,
  `pitch` int(11) NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `meshsize`
--

LOCK TABLES `meshsize` WRITE;
/*!40000 ALTER TABLE `meshsize` DISABLE KEYS */;
INSERT INTO `meshsize` VALUES ('200',90,35,125),('300',58,25,83),('400',37,25,62);
/*!40000 ALTER TABLE `meshsize` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `microscope`
--

DROP TABLE IF EXISTS `microscope`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `microscope` (
  `name` varchar(100) NOT NULL,
  `location` varchar(30) NOT NULL,
  `voltage` int(11) NOT NULL,
  `spherical_abberation` double NOT NULL,
  `microscope_id` varchar(30) NOT NULL,
  `loader_size` int(11) NOT NULL,
  `worker_hostname` varchar(30) NOT NULL,
  `executable` varchar(30) NOT NULL,
  `serialem_IP` varchar(30) NOT NULL,
  `serialem_PORT` int(11) NOT NULL,
  `windows_path` varchar(200) NOT NULL,
  `scope_path` varchar(200) NOT NULL,
  PRIMARY KEY (`microscope_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `microscope`
--

LOCK TABLES `microscope` WRITE;
/*!40000 ALTER TABLE `microscope` DISABLE KEYS */;
INSERT INTO `microscope` VALUES ('fake_scope','test',200,2.7,'h0PgRUjUq2K2Cr1CGZJq3q08il8i5n',12,'localhost','smartscope.py','xxx.xxx.xxx.xxx',48888,'X:\\\\auto_screening\\','/mnt/fake_scope');
/*!40000 ALTER TABLE `microscope` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `process`
--

DROP TABLE IF EXISTS `process`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `process` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `PID` int(11) NOT NULL,
  `start_time` datetime(6) NOT NULL,
  `end_time` datetime(6) DEFAULT NULL,
  `status` varchar(10) NOT NULL,
  `session_id_id` varchar(30) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `process_session_id_id_d846cfec_fk_screeningsession_session_id` (`session_id_id`),
  CONSTRAINT `process_session_id_id_d846cfec_fk_screeningsession_session_id` FOREIGN KEY (`session_id_id`) REFERENCES `screeningsession` (`session_id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `process`
--

LOCK TABLES `process` WRITE;
/*!40000 ALTER TABLE `process` DISABLE KEYS */;
/*!40000 ALTER TABLE `process` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `screeningsession`
--

DROP TABLE IF EXISTS `screeningsession`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `screeningsession` (
  `session` varchar(30) NOT NULL,
  `date` varchar(8) NOT NULL,
  `version` varchar(8) NOT NULL,
  `working_dir` varchar(300) NOT NULL,
  `session_id` varchar(30) NOT NULL,
  `detector_id_id` int(11) DEFAULT NULL,
  `group_id` varchar(150) DEFAULT NULL,
  `microscope_id_id` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  KEY `screeningsession_detector_id_id_703010a5_fk_detector_id` (`detector_id_id`),
  KEY `screeningsession_group_id_f67b3201_fk_auth_group_name` (`group_id`),
  KEY `screeningsession_microscope_id_id_6d084875_fk_microscop` (`microscope_id_id`),
  CONSTRAINT `screeningsession_detector_id_id_703010a5_fk_detector_id` FOREIGN KEY (`detector_id_id`) REFERENCES `detector` (`id`),
  CONSTRAINT `screeningsession_group_id_f67b3201_fk_auth_group_name` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`name`),
  CONSTRAINT `screeningsession_microscope_id_id_6d084875_fk_microscop` FOREIGN KEY (`microscope_id_id`) REFERENCES `microscope` (`microscope_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `screeningsession`
--

LOCK TABLES `screeningsession` WRITE;
/*!40000 ALTER TABLE `screeningsession` DISABLE KEYS */;
/*!40000 ALTER TABLE `screeningsession` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `selector`
--

DROP TABLE IF EXISTS `selector`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `selector` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `object_id` varchar(30) NOT NULL,
  `method_name` varchar(50) DEFAULT NULL,
  `label` varchar(30) DEFAULT NULL,
  `content_type_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `selector_content_type_id_3e5dbd50_fk_django_content_type_id` (`content_type_id`),
  CONSTRAINT `selector_content_type_id_3e5dbd50_fk_django_content_type_id` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=76524 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `selector`
--

LOCK TABLES `selector` WRITE;
/*!40000 ALTER TABLE `selector` DISABLE KEYS */;
/*!40000 ALTER TABLE `selector` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `squaremodel`
--

DROP TABLE IF EXISTS `squaremodel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `squaremodel` (
  `name` varchar(100) NOT NULL,
  `number` int(11) NOT NULL,
  `pixel_size` double DEFAULT NULL,
  `shape_x` int(11) DEFAULT NULL,
  `shape_y` int(11) DEFAULT NULL,
  `selected` tinyint(1) NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `completion_time` datetime(6) DEFAULT NULL,
  `square_id` varchar(30) NOT NULL,
  `area` double DEFAULT NULL,
  `atlas_id_id` varchar(30) NOT NULL,
  `grid_id_id` varchar(30) NOT NULL,
  PRIMARY KEY (`square_id`),
  UNIQUE KEY `squaremodel_name_atlas_id_id_cdc2974a_uniq` (`name`,`atlas_id_id`),
  KEY `squaremodel_atlas_id_id_89647666_fk_atlasmodel_atlas_id` (`atlas_id_id`),
  KEY `squaremodel_grid_id_id_775a3fee_fk_autoloadergrid_grid_id` (`grid_id_id`),
  CONSTRAINT `squaremodel_atlas_id_id_89647666_fk_atlasmodel_atlas_id` FOREIGN KEY (`atlas_id_id`) REFERENCES `atlasmodel` (`atlas_id`),
  CONSTRAINT `squaremodel_grid_id_id_775a3fee_fk_autoloadergrid_grid_id` FOREIGN KEY (`grid_id_id`) REFERENCES `autoloadergrid` (`grid_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `squaremodel`
--

LOCK TABLES `squaremodel` WRITE;
/*!40000 ALTER TABLE `squaremodel` DISABLE KEYS */;
/*!40000 ALTER TABLE `squaremodel` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-07-02 11:05:09
