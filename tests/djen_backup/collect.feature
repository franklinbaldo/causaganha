Feature: Collect and upload
  The system downloads ZIPs from the DJEN proxy and uploads them
  to the Internet Archive.

  Scenario: Successfully download and upload a ZIP
    Given DJEN proxy returns a caderno URL for "TJSP" on "2024-01-15"
    And the caderno URL serves a valid ZIP of 1024 bytes
    And Internet Archive accepts uploads
    When I process the item "TJSP" on "2024-01-15"
    Then the ZIP should be uploaded to Internet Archive as "djen-2024-01-15-TJSP.zip"
    And the upload should include correct IA S3 headers
    And the state should mark "TJSP" on "2024-01-15" as "uploaded"

  Scenario: Upload includes Content-MD5 header
    Given DJEN proxy returns a caderno URL for "TRT1" on "2024-05-20"
    And the caderno URL serves a valid ZIP of 2048 bytes
    And Internet Archive accepts uploads
    When I process the item "TRT1" on "2024-05-20"
    Then the upload Content-MD5 should match the file's MD5 hash

  Scenario: Idempotent — already uploaded item is skipped
    Given Internet Archive has files for "2024-01-15":
      | filename                   |
      | backup-djen-2024-01-15-TJSP.zip   |
    And the tribunal list is:
      | tribunal |
      | TJSP     |
    When I detect gaps for "2024-01-15"
    Then there should be no gaps
