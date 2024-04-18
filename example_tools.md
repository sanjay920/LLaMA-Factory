# Example tools

```
[{"name":"download","description":"Downloads a URL, saving the contents to disk at a given location","parameters":{"type":"object","properties":{"location":{"description":"(optional) The on disk location to store the file. If no location is specified a temp location will be used. If the target file already exists it will fail unless override is set to true.","type":"string"},"override":{"description":"If true and a file at the location exists, the file will be overwritten, otherwise fail. Default is false","type":"string"},"url":{"description":"The URL to download, either http or https.","type":"string"}}}},{"name":"execute","description":"Execute a command and get the output of the command","parameters":{"type":"object","properties":{"command":{"description":"The command to run including all applicable arguments","type":"string"},"directory":{"description":"The directory to use as the current working directory of the command. The current directory \".\" will be used if no argument is passed","type":"string"}}}},{"name":"delete","description":"Removes the specified files","parameters":{"type":"object","properties":{"location":{"description":"The file to remove","type":"string"}}}}]
```


```
{
  "model": "gpt-4-turbo-preview",
  "messages": [
    {
      "role": "system",
      "content": "\nYou are task oriented system.\nYou receive input from a user, process the input from the given instructions, and then output the result.\nYour objective is to provide consistent and correct results.\nYou do not need to explain the steps taken, only provide the result to the given instructions.\nYou are referred to as a tool.\n"
    },
    {
      "role": "system",
      "content": "Download https://www.sqlitetutorial.net/wp-content/uploads/2018/03/chinook.zip to a\nrandom file. Then expand the archive to a temporary location as there is a sqlite\ndatabase in it.\n\nFirst inspect the schema of the database to understand the table structure.\n\nForm and run a SQL query to find the artist with the most number of albums and output\nthe result of that.\n\nWhen done remove the database file and the downloaded content."
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_MSly98DJWiJhqBhWBHivRk00",
          "type": "function",
          "function": {
            "name": "download_from_url",
            "arguments": "{\"url\":\"https://www.sqlitetutorial.net/wp-content/uploads/2018/03/chinook.zip\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "/tmp/gpt-download58271901",
      "tool_call_id": "call_MSly98DJWiJhqBhWBHivRk00"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_B4I2PbroCuTdTwdarqZSNFmn",
          "type": "function",
          "function": {
            "name": "execute",
            "arguments": "{\"command\":\"unzip /tmp/gpt-download58271901 -d /tmp/chinook\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "Archive:  /tmp/gpt-download58271901\n  inflating: /tmp/chinook/chinook.db  \n",
      "tool_call_id": "call_B4I2PbroCuTdTwdarqZSNFmn"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_MpaVVfQ47fWaX7wBImHqdq7k",
          "type": "function",
          "function": {
            "name": "execute",
            "arguments": "{\"command\":\"sqlite3 /tmp/chinook/chinook.db \\\".schema\\\"\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "CREATE TABLE IF NOT EXISTS \"albums\"\r\n(\r\n    [AlbumId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Title] NVARCHAR(160)  NOT NULL,\r\n    [ArtistId] INTEGER  NOT NULL,\r\n    FOREIGN KEY ([ArtistId]) REFERENCES \"artists\" ([ArtistId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE sqlite_sequence(name,seq);\nCREATE TABLE IF NOT EXISTS \"artists\"\r\n(\r\n    [ArtistId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Name] NVARCHAR(120)\r\n);\nCREATE TABLE IF NOT EXISTS \"customers\"\r\n(\r\n    [CustomerId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [FirstName] NVARCHAR(40)  NOT NULL,\r\n    [LastName] NVARCHAR(20)  NOT NULL,\r\n    [Company] NVARCHAR(80),\r\n    [Address] NVARCHAR(70),\r\n    [City] NVARCHAR(40),\r\n    [State] NVARCHAR(40),\r\n    [Country] NVARCHAR(40),\r\n    [PostalCode] NVARCHAR(10),\r\n    [Phone] NVARCHAR(24),\r\n    [Fax] NVARCHAR(24),\r\n    [Email] NVARCHAR(60)  NOT NULL,\r\n    [SupportRepId] INTEGER,\r\n    FOREIGN KEY ([SupportRepId]) REFERENCES \"employees\" ([EmployeeId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE IF NOT EXISTS \"employees\"\r\n(\r\n    [EmployeeId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [LastName] NVARCHAR(20)  NOT NULL,\r\n    [FirstName] NVARCHAR(20)  NOT NULL,\r\n    [Title] NVARCHAR(30),\r\n    [ReportsTo] INTEGER,\r\n    [BirthDate] DATETIME,\r\n    [HireDate] DATETIME,\r\n    [Address] NVARCHAR(70),\r\n    [City] NVARCHAR(40),\r\n    [State] NVARCHAR(40),\r\n    [Country] NVARCHAR(40),\r\n    [PostalCode] NVARCHAR(10),\r\n    [Phone] NVARCHAR(24),\r\n    [Fax] NVARCHAR(24),\r\n    [Email] NVARCHAR(60),\r\n    FOREIGN KEY ([ReportsTo]) REFERENCES \"employees\" ([EmployeeId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE IF NOT EXISTS \"genres\"\r\n(\r\n    [GenreId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Name] NVARCHAR(120)\r\n);\nCREATE TABLE IF NOT EXISTS \"invoices\"\r\n(\r\n    [InvoiceId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [CustomerId] INTEGER  NOT NULL,\r\n    [InvoiceDate] DATETIME  NOT NULL,\r\n    [BillingAddress] NVARCHAR(70),\r\n    [BillingCity] NVARCHAR(40),\r\n    [BillingState] NVARCHAR(40),\r\n    [BillingCountry] NVARCHAR(40),\r\n    [BillingPostalCode] NVARCHAR(10),\r\n    [Total] NUMERIC(10,2)  NOT NULL,\r\n    FOREIGN KEY ([CustomerId]) REFERENCES \"customers\" ([CustomerId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE IF NOT EXISTS \"invoice_items\"\r\n(\r\n    [InvoiceLineId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [InvoiceId] INTEGER  NOT NULL,\r\n    [TrackId] INTEGER  NOT NULL,\r\n    [UnitPrice] NUMERIC(10,2)  NOT NULL,\r\n    [Quantity] INTEGER  NOT NULL,\r\n    FOREIGN KEY ([InvoiceId]) REFERENCES \"invoices\" ([InvoiceId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION,\r\n    FOREIGN KEY ([TrackId]) REFERENCES \"tracks\" ([TrackId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE IF NOT EXISTS \"media_types\"\r\n(\r\n    [MediaTypeId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Name] NVARCHAR(120)\r\n);\nCREATE TABLE IF NOT EXISTS \"playlists\"\r\n(\r\n    [PlaylistId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Name] NVARCHAR(120)\r\n);\nCREATE TABLE IF NOT EXISTS \"playlist_track\"\r\n(\r\n    [PlaylistId] INTEGER  NOT NULL,\r\n    [TrackId] INTEGER  NOT NULL,\r\n    CONSTRAINT [PK_PlaylistTrack] PRIMARY KEY  ([PlaylistId], [TrackId]),\r\n    FOREIGN KEY ([PlaylistId]) REFERENCES \"playlists\" ([PlaylistId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION,\r\n    FOREIGN KEY ([TrackId]) REFERENCES \"tracks\" ([TrackId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE TABLE IF NOT EXISTS \"tracks\"\r\n(\r\n    [TrackId] INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,\r\n    [Name] NVARCHAR(200)  NOT NULL,\r\n    [AlbumId] INTEGER,\r\n    [MediaTypeId] INTEGER  NOT NULL,\r\n    [GenreId] INTEGER,\r\n    [Composer] NVARCHAR(220),\r\n    [Milliseconds] INTEGER  NOT NULL,\r\n    [Bytes] INTEGER,\r\n    [UnitPrice] NUMERIC(10,2)  NOT NULL,\r\n    FOREIGN KEY ([AlbumId]) REFERENCES \"albums\" ([AlbumId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION,\r\n    FOREIGN KEY ([GenreId]) REFERENCES \"genres\" ([GenreId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION,\r\n    FOREIGN KEY ([MediaTypeId]) REFERENCES \"media_types\" ([MediaTypeId]) \r\n\t\tON DELETE NO ACTION ON UPDATE NO ACTION\r\n);\nCREATE INDEX [IFK_AlbumArtistId] ON \"albums\" ([ArtistId]);\nCREATE INDEX [IFK_CustomerSupportRepId] ON \"customers\" ([SupportRepId]);\nCREATE INDEX [IFK_EmployeeReportsTo] ON \"employees\" ([ReportsTo]);\nCREATE INDEX [IFK_InvoiceCustomerId] ON \"invoices\" ([CustomerId]);\nCREATE INDEX [IFK_InvoiceLineInvoiceId] ON \"invoice_items\" ([InvoiceId]);\nCREATE INDEX [IFK_InvoiceLineTrackId] ON \"invoice_items\" ([TrackId]);\nCREATE INDEX [IFK_PlaylistTrackTrackId] ON \"playlist_track\" ([TrackId]);\nCREATE INDEX [IFK_TrackAlbumId] ON \"tracks\" ([AlbumId]);\nCREATE INDEX [IFK_TrackGenreId] ON \"tracks\" ([GenreId]);\nCREATE INDEX [IFK_TrackMediaTypeId] ON \"tracks\" ([MediaTypeId]);\nCREATE TABLE sqlite_stat1(tbl,idx,stat);\n",
      "tool_call_id": "call_MpaVVfQ47fWaX7wBImHqdq7k"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_zdWgplixl1OtXTpYyg5toGcF",
          "type": "function",
          "function": {
            "name": "execute",
            "arguments": "{\"command\":\"sqlite3 /tmp/chinook/chinook.db \\\"SELECT artists.Name, COUNT(albums.AlbumId) AS AlbumCount FROM artists JOIN albums ON artists.ArtistId = albums.ArtistId GROUP BY artists.ArtistId ORDER BY AlbumCount DESC LIMIT 1;\\\"\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "Iron Maiden|21\n",
      "tool_call_id": "call_zdWgplixl1OtXTpYyg5toGcF"
    },
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_jzLxPuWFUpc073nYloCoCiA7",
          "type": "function",
          "function": {
            "name": "remove_file",
            "arguments": "{\"location\": \"/tmp/chinook/chinook.db\"}"
          }
        },
        {
          "index": 1,
          "id": "call_lOxH2NFC2Rcs1ZBez9cCD9w6",
          "type": "function",
          "function": {
            "name": "remove_file",
            "arguments": "{\"location\": \"/tmp/gpt-download58271901\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "Removed file: /tmp/chinook/chinook.db",
      "tool_call_id": "call_jzLxPuWFUpc073nYloCoCiA7"
    },
    {
      "role": "tool",
      "content": "Removed file: /tmp/gpt-download58271901",
      "tool_call_id": "call_lOxH2NFC2Rcs1ZBez9cCD9w6"
    }
  ],
  "temperature": 0,
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "download_from_url",
        "description": "Downloads a URL, saving the contents to disk at a given location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "description": "(optional) The on disk location to store the file. If no location is specified a temp location will be used. If the target file already exists it will fail unless override is set to true.",
              "type": "string"
            },
            "override": {
              "description": "If true and a file at the location exists, the file will be overwritten, otherwise fail. Default is false",
              "type": "string"
            },
            "url": {
              "description": "The URL to download, either http or https.",
              "type": "string"
            }
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "execute",
        "description": "Execute a command and get the output of the command",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "description": "The command to run including all applicable arguments",
              "type": "string"
            },
            "directory": {
              "description": "The directory to use as the current working directory of the command. The current directory \".\" will be used if no argument is passed",
              "type": "string"
            }
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "remove_file",
        "description": "Removes the specified files",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "description": "The file to remove",
              "type": "string"
            }
          }
        }
      }
    }
  ]
}

```