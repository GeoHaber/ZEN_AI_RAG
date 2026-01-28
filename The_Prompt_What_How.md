"What" are ve building

1) Read the project rules about funtionality and proposed structure its in the file zena_master_specification.md and do not deviate from it.
2) If you are not clear or later we find functionality that is not clear or missing we will add it to the zena_master_specification.md file and do not deviate from it.
3) Do a thorow design review of the needed files and tests to implement that functionality.

"How" are we going to test it, buldid, analyze health, functionality and performance.

1) each and every function must be tested well for all its functions and for that we must think firs about thestin and the about building 
    1.1) should we have self test for every thing or a separate file to test or a hybrid smoke test internaly and though coverage long test externaly ?
     1.2) how are we going to maintain these tests for funtionality and performance 
2) The moust important part the heart and brain of teh project is the local llama.cpp using the "selected" local LLM or accesing external LLMS
3) Everithing else all other functions setings displa etc are either functions to acces or control the heart and bran or to chage models or to run swars arbitrage RAG to feed local data
4) Lets understand if the files we have do what is required and if theyy do not it then lets understand what must be added or changed
5) for #4 we must think about the best way to implement it and what files must be created or changed so read and review Each and every file and folder and make a list of what must be done and what files must be created or changed
6) everithing else that we deem not neded lets remove so we dont get confused
   "Ease of Testing"
7) lets swich to a mode where we can test each function independantly and in isolation maybe switch to local mode on device not Web mode
8) Think : we have a few problems but they fit in 2 categories :
   1) UI related the ui is not working not able to start lots of NiceUI arguments etc.. Solve that in stand alone more no bac end only a test that runst the ui places all the elements and does monkey test on all the menues and buttons ... NO beckend just front and testing
   2) Bakend related ishues starting the hearth and brann llama.cpp with teh selectable model and implementing the rag feed rag read and all the other things un teh speciification.. Again create a STUB a test software that does that regardless of the UI .. 
   3) When the UI and tha back end work pass all the test then lets stich them together and fix what ever ishues we find then.
      What do you think is this the corect aproach ? 
