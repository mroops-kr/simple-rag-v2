

CREATE TABLE IF NOT EXISTS `rg_share2_file` (
  `file_id` varchar(20) NOT NULL,
  `file_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `file_path` varchar(100) NOT NULL,
  `file_ext` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `char_size` int DEFAULT NULL,
  `char_chunk_count` int DEFAULT NULL,
  `summary_size` int DEFAULT NULL,
  `summary_chunk_count` int DEFAULT NULL,
  PRIMARY KEY (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS `rg_share2_file_cont` (
  `file_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `level` int NOT NULL,
  `page` int NOT NULL,
  `p_page` int DEFAULT NULL,
  `file_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `source_pages` varchar(50) NOT NULL DEFAULT '',
  `created_at` timestamp NULL DEFAULT NULL,
  `char_size` int DEFAULT NULL,
  `text` longtext,
  PRIMARY KEY (`file_id`,`level`,`page`),
  CONSTRAINT `fk_rg_share2_file_cont` FOREIGN KEY (`file_id`) REFERENCES `rg_share2_file` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS `rg_user2_file` (
  `user_id` varchar(50) NOT NULL,
  `file_id` varchar(20) NOT NULL,
  `file_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `file_path` varchar(100) NOT NULL,
  `file_ext` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `char_size` int DEFAULT NULL,
  `char_chunk_count` int DEFAULT NULL,
  `summary_size` int DEFAULT NULL,
  `summary_chunk_count` int DEFAULT NULL,
  PRIMARY KEY (`user_id`,`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS `rg_user2_file_cont` (
  `user_id` varchar(50) NOT NULL,
  `file_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `level` int NOT NULL,
  `page` int NOT NULL,
  `p_page` int DEFAULT NULL,
  `file_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `source_pages` varchar(50) NOT NULL DEFAULT '',
  `created_at` timestamp NULL DEFAULT NULL,
  `char_size` int DEFAULT NULL,
  `text` longtext,
  PRIMARY KEY (`user_id`,`file_id`,`level`,`page`),
  CONSTRAINT `fk_rg_user2_file_cont` FOREIGN KEY (`user_id`, `file_id`) REFERENCES `rg_user2_file` (`user_id`, `file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

