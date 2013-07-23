<?php

require_once $_SESSION['config']['_ROOT_'].'/inc/lib/JsonXmlFunctions.php';

/**
 * Mongodb Class
 * @param $username: the user name to access the database
 * @param $password: the user password to access the database
 * @param $server: the server ip address
 * @param $port: the port number to access the server
 * @param $database: the database name
 */
Class MongoDBStream
{

	private $server;
	private $databaseName;
	private $username;
	private $password;
	private $port;
	private $connection;
	private $databaseObject;

	// Logging variables
	private $LOGGER;
	private static $LEVELS = array(
			'DBG' => 'notice',
			'NO_DBG' => 'info'
	);
	private static $LOG_FILE;
	private static $FILE_NAME = 'MongoDBStream.php';
	
	/**
	 * Class constructor
	 */
	function __construct()
	{
		self::$LOG_FILE = $_SESSION['xsd_parser']['conf']['logs_dirname'].'/mongodb.log';
		
		$argc = func_num_args();
		$argv = func_get_args();

		switch($argc)
		{
			case 0 :
				$this -> server = "127.0.0.1";
				$this -> port = 27017;
				$level = self::$LEVELS['NO_DBG'];
				break;
			case 1 :
				$this -> server = $argv[0];
				$this -> port = 27017;
				$level = self::$LEVELS['NO_DBG'];
				break;
			case 2 :
				$this -> server = $argv[0];
				$this -> port = 27017;
				$this -> databaseName = $argv[1];
				$level = self::$LEVELS['NO_DBG'];
				break;
			case 3 :
				$this -> server = $argv[0];
				$this -> port = 27017;
				$this -> username = $argv[1];
				$this -> password = $argv[2];
				$level = self::$LEVELS['NO_DBG'];
				break;
			case 4 :
				$this -> server = $argv[0];
				$this -> port = 27017;
				$this -> databaseName = $argv[1];
				$this -> username = $argv[2];
				$this -> password = $argv[3];
				$level = self::$LEVELS['NO_DBG'];
				break;
			case 5 :
				$this -> server = $argv[0];
				$this -> databaseName = $argv[1];
				$this -> port = $argv[2];
				$this -> username = $argv[3];
				$this -> password = $argv[4];
				$level = self::$LEVELS['NO_DBG'];
				break;
			default :
				$this -> LOGGER -> log_error("Invalid argument number: Should be more than 5", 'MongoDBStream::__construct');
				break;
		}
		
		try
		{
			$this -> LOGGER = new Logger($level, self::$LOG_FILE, self::$FILE_NAME);
		}
		catch (Exception $ex)
		{
			echo '<b>Impossible to build the Logger:</b><br/>' . $ex -> getMessage();
			return;
		}
		
		$this -> connect();
	}

	public function getDatabaseName()
	{
		return $this -> databaseName;
	}

	public function getDatabaseObject()
	{
		return $this -> databaseObject;
	}

	public function getConnection()
	{
		return $this -> connection;
	}

	public function setDatabaseName($databaseName)
	{
		$this -> databaseName = $databaseName;
	}

	function getCollection($collectionName)
	{
		return new MongoCollection($this -> databaseObject, $collectionName);
	}

	/**
	 * Method to connect to the mongod instance
	 */
	public function connect()
	{
		try
		{
			// Attempt to connect with a persistent connection. Must be used as it enhances database performance
			if (!($this -> username == null || $this -> password == null))
				$connection = new Mongo("mongodb://{$this->username}:{$this->password}@{$this->server}:{$this->port}");
			else
				$connection = new Mongo("mongodb://{$this->server}:{$this->port}");
			$this -> connection = $connection;
		}
		catch (MongoConnectionException $e)
		{
			throw new Exception("Cannot connect to the database",-1);
			$this -> LOGGER -> log_error("Cannot connect to the database", 'MongoDBStream::connect');
		}
	}

	/**
	 * Method to connect to the database
	 */
	public function openDB()
	{
		try
		{
			// Attempt to connect with a persistent connection. Must be used as it enhances database performance
			if (isset($this -> databaseName) && isset($this -> connection) && trim($this -> databaseName) != "")
				$this -> databaseObject = new MongoDB($this -> connection, $this -> databaseName);
			else
			{
				throw new Exception("Database Object not set",-2);
				$this -> LOGGER -> log_error("Database Object not set", 'MongoDBStream::openDB');
			}
		}
		catch (Exception $e)
		{
			throw new Exception("Issue with the MongoDB database",-3);
			$this -> LOGGER -> log_error("Issue with the MongoDB database", 'MongoDBStream::openDB');
		}
	}

	// There is no explicit need to disconnect from the database

	/**
	 * Method to insert a JSON document into the database
	 * @param $doc: string that describe the path of the file
	 * @param $collection: the collection in which the document is pushed
	 */
	function insertJsonFromFile($doc, $collectionName)
	{
		// Get the JSON file content
		$jsonString = file_get_contents($doc);
		insertJson($jsonString, $collectionName);
	}

	/**
	 *
	 * @param string $jsonString
	 * @param string $collectionName
	 */
	function insertJson($jsonArray, $collectionName)
	{
		// Insert it into the collection
		if (isset($this -> databaseObject))
		{
			$collectionObject = new MongoCollection($this -> databaseObject, $collectionName);
			$collectionObject -> save($jsonArray, array("w" => 1));
			
			//var_dump($jsonArray["_id"]);
			
			return $jsonArray["_id"];
		}
		else
		{
			throw new Exception("Database Object not set",-2);
			$this -> LOGGER -> log_error("Database Object not set", 'MongoDBStream::insertJson');
		}
	}

	/**
	 * Method to insert a XML document into the database, used as a test function. Do not use in production.
	 * @param $doc: string that describe the path of the file
	 * @param $collection: the collection in which the document is pushed
	 */
	function insertXml($xmlString, $collectionName)
	{
		$dom = DOMDocument::loadXML($xmlString);
		
		// Translate the XML content into JSON content
		$jsonArray = encodeBadgerFish($dom);
		
		if ($jsonArray == array())
		{
			throw new Exception("Could not proceed to the JSON conversion",-4);
			$this -> LOGGER -> log_error("Could not proceed to the JSON conversion", 'MongoDBStream::insertXml');
		}
		
		// Insert it into the collection
		$this -> insertJson($jsonArray, $collectionName);

	}

	/**
	 * Method to insert a XML document into the database, used as a test function. Do not use in production.
	 * @param $doc: string that describe the path of the file
	 * @param $collection: the collection in which the document is pushed
	 */
	function insertXmlWithId($xmlString, $documentId, $collectionName)
	{
		$document = new DOMDocument();
		$document->loadXML($xmlString);
		
		// Translate the XML content into JSON content
		$jsonArray = encodeBadgerFish($document);
		
		if ($jsonArray == array())
		{
			throw new Exception("Could not proceed to the JSON conversion",-4);
			$this -> LOGGER -> log_error("Could not proceed to the JSON conversion", 'MongoDBStream::insertXmlWithId');
		}
		
		$jsonArray['_id'] = $documentId;
		
		// Insert it into the collection
		$this -> insertJson($jsonArray, $collectionName);

	}

	function removeIdFromCollection($documentId, $collectionName)
	{
		$idArray = array('_id' => $documentId);
		
		$collectionObject = new MongoCollection($this -> databaseObject, $collectionName);
		$collectionObject -> remove($idArray/*, true*/);
	}

	function retrieveXml($doc, $collectionName)
	{
		$json_data = file_get_contents($doc);

		$xmlContents = decodeBadgerFish($json_data);
		if (!$xmlContents)
		{
			throw new Exception("Could not proceed to the JSON conversion",-4);
			$this -> LOGGER -> log_error("Could not proceed to the JSON conversion", 'MongoDBStream::retrieveXml');
		}
		
		return htmlspecialchars($xmlContents -> saveXML());
	}

	function queryData($query, $collectionName, $projection = array())
	{
		try
		{
			if (isset($this -> databaseObject))
			{
				$collectionObject = new MongoCollection($this -> databaseObject, $collectionName);
				//Execute the query
				return $collectionObject -> find($query, $projection);
			}
			else
			{
				throw new Exception("Database Object not set",-2);
				$this -> LOGGER -> log_error("Database Object not set", 'MongoDBStream::queryData');
			}
		}
		catch(MongoCursorException $e)
		{
			throw new Exception("Issue with the query",-5);
			$this -> LOGGER -> log_error("Issue with the query", 'MongoDBStream::queryData');
		}
	}

}
?>
