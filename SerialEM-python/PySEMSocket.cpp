// PySEMSocket.cpp - Socket interface based on BaseSocket.cpp in SerialEM, with
// removal of statics and multiple socket support, modification of image receiving to
// deal with image properties being received instead of expected, and addition of
// image sending code from BaseServer.cpp in FeiScope, similarly modified to send
// properties and to skip the handshakes.  Handshakes did NOT work in that direction

#include <sys/types.h>
#include <sys/stat.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#include "PySEMSocket.h"

#define EXTERNAL_PY_PORT 48888

#ifdef _WIN32

// Windows definitions
#define DUPENV(a, b, c) _dupenv_s(&a, b, c);
#define FREE_ENV(a)  free(a)
#else

// Unix includes and definitions
#include <sys/time.h>
#include <errno.h>
#include <unistd.h>

#define _strdup strdup
#define DUPENV(a, b, c) a = getenv(c)
#define FREE_ENV(a)
#define closesocket close
#define WSAECONNABORTED ECONNREFUSED
#define WSAECONNRESET ECONNREFUSED

int WSAGetLastError()
{
  return errno;
}

unsigned int GetTickCount()
{
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return (unsigned int)(1000 * tv.tv_sec + tv.tv_usec / 1000);
}
#endif

// Copy of tick interval functions
double SEMTickInterval(double now, double then)
{
  double retval = now - then;
  if (retval < -2147483648.)
    retval += 4294967296.;
  else if (retval > 2147483648.)
    retval -= 4294967296.;
  return retval;
}
double SEMTickInterval(double then)
{
  return SEMTickInterval((double)GetTickCount(), then);
}

//  Constructor
CPySEMSocket::CPySEMSocket(void)
{
  mWSAinitialized = false;
  mChunkSize = 16810000;
  mSuperChunkSize = 336200000;
  mIPaddress = NULL;
  mServer = INVALID_SOCKET;
  mCloseBeforeNextUse = false;
  mArgsBuffer = NULL;
  mArgBufSize = 0;
  mHandshakeCode = PSS_ChunkHandshake;
}

CPySEMSocket::~CPySEMSocket(void)
{
}

// Initialize for one socket: check the IP address, allocate the buffer, and

int CPySEMSocket::InitializeSocket(int port, const char *ipAddress)
{
  char *envar;
  static bool firstTime = true;
  if (mIPaddress && mServer != INVALID_SOCKET)
    return 0;

#ifdef _WIN32
  // Insist on at least Winsock v1.1
  const unsigned int VERSION_MAJOR = 1;
  const unsigned int VERSION_MINOR = 1;
  WSADATA WSData;
  if (!mWSAinitialized) {
    
    // Attempt to initialize WinSock (1.1 or later). 
    if (WSAStartup(MAKEWORD(VERSION_MAJOR, VERSION_MINOR), &WSData)) {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Failed to initialize Winsock");
      return 1;
    }
  }
#endif
  mWSAinitialized = true;

  // Only do the port and IP address on the first call, as later calls happen
  // automatically to restart scripting and we don't want the default
  if (firstTime) {

    // get the port if none supplied, use default for external control or environment var
    if (!port) {
      port = EXTERNAL_PY_PORT;
      DUPENV(envar, NULL, "PY_SERIALEM_PORT");
      if (envar) {
        port = atoi(envar);
        FREE_ENV(envar);
      }
    }
    if (port <= 0)  {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "The port number must be positive");
      return 1;
    }
    mPort = (unsigned short)port;
    
    // Get the IP address if none supplied, local or environment variable
    free(mIPaddress);       
    if (!ipAddress) {
      DUPENV(envar, NULL, "PY_SERIALEM_IP");
      if (envar) {
        mIPaddress = _strdup(envar);
        FREE_ENV(envar);
      } else
        mIPaddress = _strdup("127.0.0.1");
    } else {
      mIPaddress = _strdup(ipAddress);
    }
    if (!mIPaddress) {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "failed to duplicate IP address");
      return 1;
    }
    firstTime = false;
  }

  // Allocate buffer
  if (!mArgsBuffer) {
    mArgsBuffer = (char *)malloc(ARGS_BUFFER_CHUNK);
    if (!mArgsBuffer) {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Failed to allocate little buffer");
      return 1;
    }
    mArgBufSize = ARGS_BUFFER_CHUNK;
  }

  return OpenServerSocket();
}

// Reallocate the argument buffer if needed; if it fails, return 1 and leave things as
// they were
int CPySEMSocket::ReallocArgsBufIfNeeded(int needSize)
{
  int newSize;
  char *newBuf;
  if (needSize < mArgBufSize - 3)
    return 0;
  newSize = ((needSize + ARGS_BUFFER_CHUNK - 1) / ARGS_BUFFER_CHUNK) * ARGS_BUFFER_CHUNK;
  newBuf = (char *)malloc(newSize);
  if (!newBuf)
    return 1;
  memcpy(newBuf, mArgsBuffer, mArgBufSize);
  free(mArgsBuffer);
  mArgBufSize = newSize;
  mArgsBuffer = newBuf;
  return 0;
}

// Call once to uninitialize on program end
void CPySEMSocket::UninitializeWSA(void)
{
#ifdef _WIN32
  if (mWSAinitialized)
    WSACleanup();
#endif
  mWSAinitialized = false;
  free(mIPaddress);
  mIPaddress = NULL;
  free(mArgsBuffer);
  mArgsBuffer = NULL;
}


void CPySEMSocket::CloseBeforeNextUse()
{
  mCloseBeforeNextUse = true;
}

// Open the socket and connect it to the server
int CPySEMSocket::OpenServerSocket()
{
#ifdef _WIN32
  mSockAddr.sin_addr.S_un.S_addr = inet_addr(mIPaddress); 
  memset(mSockAddr.sin_zero, '\0', sizeof(mSockAddr.sin_zero));
#else
  memset(&mSockAddr, 0, sizeof(mSockAddr));
  inet_pton(AF_INET, mIPaddress, &mSockAddr.sin_addr );
#endif
  mSockAddr.sin_family = AF_INET;
  mSockAddr.sin_port = htons(mPort);     // short, network byte order

  mServer = socket(PF_INET, SOCK_STREAM, 0);
  if(mServer == INVALID_SOCKET) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Cannot open server socket at "
              "IP %s on port %d (%d)", mIPaddress, mPort, WSAGetLastError());
    return 1;
  }

  // Connect the Socket.
  if(connect(mServer, (PSOCKADDR) &mSockAddr, sizeof(SOCKADDR_IN))) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Error connecting to Server socket "
              "at IP %s on port %d (%d)" , mIPaddress, mPort, WSAGetLastError());
    CloseServer();
    return 1;
  }
  sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Connected to Server socket at IP %s "
            "on port %d", mIPaddress, mPort);
  return 0;
}

// Close the socket and mark it as invalid
void CPySEMSocket::CloseServer()
{
  closesocket(mServer);
  mServer = INVALID_SOCKET;
  mCloseBeforeNextUse = false;
}

// Send a message in the argument buffer to the server and get a reply
// returns 1 for an error, and the negative of the number of bytes received if
// it is not as many as are needed for the command so that can be reponded to later
int CPySEMSocket::ExchangeMessages()
{
  int nbytes, err, trial, numReceived, numExpected, needed;
  double startTime, timeDiff;
  if (!mWSAinitialized) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Winsock not initialized");
    return 1;
  }
  if (mCloseBeforeNextUse)
    CloseServer();
  if (mServer == INVALID_SOCKET && OpenServerSocket()) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Failed to open socket");
    return 1;
  }
  for (trial = 0; trial < 2; trial++) {

    // Try to send the message
    nbytes = (int)send(mServer, mArgsBuffer, mNumBytesSend, 0);
    //SEMTrace('1', "PySEMSocket: send returned %d", nbytes);
    if (nbytes <= 0) {

      // If that fails, close the server, and on first trial, reopen it and try again
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: send error %d", WSAGetLastError());
      CloseServer();
      if (trial || OpenServerSocket()) {
        sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: send error %d on trial %d",
                  WSAGetLastError(), trial);
        return 1;
      }
      continue;
    }

    // Make sure everything was sent; if this fails give up
    if (FinishSendingBuffer(mArgsBuffer, mNumBytesSend, 
      nbytes)) {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: send error %d when finishing "
                "sending buffer", WSAGetLastError());
      CloseServer();
      return 1;
    }

    // Try to get the reply
    startTime = GetTickCount();
    numReceived = (int)recv(mServer, mArgsBuffer, mArgBufSize, 0);
    if (numReceived <= 0) {

      // If that fails with lost connection within a short time on first try, reopen
      // and try again
      err = WSAGetLastError();
      timeDiff = SEMTickInterval(startTime);
      if ((numReceived == 0 || err == WSAECONNABORTED || err == WSAECONNRESET) && 
        timeDiff < 200.) {
        sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: recv error %d after %.0f, "
                  "retry %d", err, timeDiff, 1 - trial);
        CloseServer();
        if (trial || OpenServerSocket()) {
          sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: recv error %d on trial %d",
                    err, trial); //want
          return 1;
        }
      }
    } else
      break;
  }

  // Find out how many bytes are in message and make sure we have the whole thing
  memcpy(&numExpected, &mArgsBuffer[0], sizeof(int));
  ReallocArgsBufIfNeeded(numExpected);
  if (FinishGettingBuffer(mArgsBuffer, numReceived, numExpected, 
                          mArgBufSize)) {
    CloseServer();
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: recv error %d when finishing "
              "getting args buffer", WSAGetLastError()); //want
    return 1;
  }
  if (numExpected > mArgBufSize) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: received message too big "
              "(%d bytes) for arg buffer", numExpected);  //want
    return 1;
  }
  
  needed = sizeof(int) + mNumLongRecv * sizeof(LONG) + mNumBoolRecv * 
    sizeof(BOOL) + mNumDblRecv * sizeof(double);

  if ((!mRecvLongArray && needed != numExpected) ||
    (mRecvLongArray && needed > numExpected))
    return -numExpected;
  return 0;
}

// Make sure the entire message has been received, based on initial byte count
int CPySEMSocket::FinishGettingBuffer(char *buffer, int numReceived, 
                                      int numExpected, int bufSize)
{
  int numNew, ind;
  while (numReceived < numExpected) {

    // If message is too big for buffer, just get it all and throw away the start
    ind = numReceived;
    if (numExpected > bufSize)
      ind = 0;
    numNew = (int)recv(mServer, &buffer[ind], bufSize - ind, 0);
    if (numNew <= 0) {
      return 1;
    }
    numReceived += numNew;
  }
  return 0;
}

// Send all or the remainder of a buffer
int CPySEMSocket::FinishSendingBuffer(char *buffer, int numBytes,
                                      int numTotalSent)
{
  int numToSend, numSent;
  while (numTotalSent < numBytes) {
    numToSend = numBytes - numTotalSent;
    if (numToSend > mChunkSize)
      numToSend = mChunkSize;
    numSent = (int)send(mServer, &buffer[numTotalSent], numToSend, 0);
    if (numSent < 0) {
      return 1;
    }
    numTotalSent += numSent;
  }
  return 0;
}


/////////////////////////////////////////////////////////////////////
// Support functions for the function calls

// Set the variables for starting to exchange a message, putting function code in first
// long argument position
void CPySEMSocket::InitializePacking(int funcCode)
{
  mLongArgs[0] = funcCode;
  mNumLongSend = 1;
  mNumDblSend = 0;
  mNumBoolSend = 0;
  mNumLongRecv = 0;
  mNumDblRecv = 0;
  mNumBoolRecv = 0;
  mRecvLongArray = false;
  mLongArray = NULL;
}

// Once arguments have been placed in the arrays, this routine packs them into a message,
// sends the message, received the reply, unpacks it into the argument arrays, and sets
// the return code to a negative value in various error cases
void CPySEMSocket::SendAndReceiveArgs()
{
  mErrorBuf[0] = 0x00;

 // This value was set to actual arguments for clarity; add one now for the return value
 mNumLongRecv++;
 int funcCode = mLongArgs[0];
 if (PackDataToSend()) {
   mLongArgs[0] = -1;
   sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Data to send are too large for "
             "argument buffer");
   return;
 }
 int err = ExchangeMessages();
 if (err > 0) {
   mLongArgs[0] = -8;
   return;
 }
 if (UnpackReceivedData(-err)) {
   mLongArgs[0] = -1;
   sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Received data are too large for "
             "argument buffer");
   return;
 }
 if (mLongArgs[0] == -9) {
   sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Server returned -9, which means "
             "SerialEM was disconnected and is now busy");
   return;
 }
 
 if (mLongArgs[0] < 0) {
   sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Server return code %d", mLongArgs[0]);
   return;
 }
 if (err < 0) {
   sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: wrong number of bytes received (%d) "
             "than needed for function %d", -err, funcCode);
   mLongArgs[0] = -1;
 }
}

// Simply call a function with one integer argument
int CPySEMSocket::SendOneArgReturnRetVal(int funcCode, int argument)
{
  InitializePacking(funcCode);
  mLongArgs[mNumLongSend++] = argument;
  SendAndReceiveArgs();
  return mLongArgs[0];
}

// Call a function with no arguments to return a string
const char *CPySEMSocket::GetOneString(int funcCode)
{
  static const char *empty = "";
  InitializePacking(funcCode);
  mRecvLongArray = true;
  mNumLongRecv = 1;
  SendAndReceiveArgs();
  if (mLongArgs[0])
    return empty;
  return (const char *)mLongArray;
}

// Adds a string as a long array after copying it into the supplied array; this should be
// called AFTER all long arguments are added
void CPySEMSocket::AddStringAsLongArray(const char *name, LONG *longArr, 
                                              int maxLen)
{
  int len = ((int)strlen(name) + 4) / 4;
  if (len > maxLen)
    len = maxLen;
  strncpy_s((char *)longArr, maxLen * 4, name, _TRUNCATE);
  mLongArray = longArr;
  mLongArgs[mNumLongSend++] = len;
}

// Adds an optional array of longs then an optional collection of strings by allocating
// an array and returning it; this should be called AFTER all long arguments are added
LONG *CPySEMSocket::AddLongsAndStrings(LONG *longVals, int numLongs, 
                                      const char **strings, int numStrings)
{
  int ind, len, charsLeft, lenTot = numLongs * sizeof(LONG);
  LONG *longArr;
  char *nameStr;
  for (ind = 0; ind < numStrings; ind++) 
    lenTot += (int)strlen(strings[ind]) + 1;
  lenTot = (lenTot + 5) / 4;
  longArr = (LONG *)malloc(lenTot * sizeof(LONG));
  if (!longArr)
    return NULL;

  // Pack the names after the binnings and terminate with an empty string (not needed...)
  nameStr = (char *)(&longArr[numLongs]);
  charsLeft = (lenTot - numLongs) * sizeof(LONG) - 1;
  for (ind = 0; ind < numLongs; ind++)
    longArr[ind] = longVals[ind];
  for (ind = 0; ind < numStrings; ind++) {
    strncpy_s(nameStr, charsLeft, strings[ind], _TRUNCATE);
    len = (int)strlen(strings[ind]) + 1;
    nameStr += len;
    charsLeft -= len;
  }
  nameStr[0] = 0x00;
  mLongArray = longArr;
  mLongArgs[mNumLongSend++] = lenTot;
  return longArr;
}

LONG *CPySEMSocket::AddItemArrays() 
{
  int numLongs = mScriptData->lastNonEmptyInd + 1;
  int ind, len, charsLeft, lenTot = numLongs * (sizeof(LONG) + sizeof(double));
  LONG *longArr;
  char *nameStr;
  for (ind = 0; ind < numLongs; ind++) 
    lenTot += (int)mScriptData->strItems[ind].size() + 1;
  lenTot = (lenTot + 5) / 4;
  longArr = (LONG *)malloc(lenTot * sizeof(LONG));
  if (!longArr)
    return NULL;
  
  // Pack the data and terminate with an empty string (not needed...)
  charsLeft = (lenTot - numLongs) * sizeof(LONG) - 1;
  for (ind = 0; ind < numLongs; ind++)
    longArr[ind] = mScriptData->itemInt[ind];
  nameStr = (char *)(&longArr[numLongs]);
  memcpy(nameStr, &mScriptData->itemDbl[0], numLongs * sizeof(double));
  charsLeft -= numLongs * sizeof(double);
  nameStr += numLongs * sizeof(double);

  for (ind = 0; ind < numLongs; ind++) {
    strncpy_s(nameStr, charsLeft, mScriptData->strItems[ind].c_str(), _TRUNCATE);
    len = (int)mScriptData->strItems[ind].size() + 1;
    nameStr += len;
    charsLeft -= len;
  }
  nameStr[0] = 0x00;
  mLongArray = longArr;
  mLongArgs[mNumLongSend++] = lenTot;
  return longArr;
}


// Exchanges messages for an image acquisition then, if all is good, acquires the image
// buffer of the expected size
int CPySEMSocket::ReceiveImage(char *imArray, int numBytes, int numChunks)
{
  int nsent, chunkSize, numToGet, chunk, totalRecv = 0;

  memset(imArray, 0, numBytes);  // ?
  chunkSize = (numBytes + numChunks - 1) / numChunks;
  for (chunk = 0; chunk < numChunks; chunk++) {
    if (chunk) {
      InitializePacking(mHandshakeCode);
      if (PackDataToSend()) {
        mCloseBeforeNextUse = true;
        return 1;
      }
      nsent = (int)send(mServer, mArgsBuffer, mNumBytesSend, 0);
      if (nsent <= 0) {
        sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: send error %d sending "
                  "image handshake", WSAGetLastError());
        CloseServer();
        return 1;
      }
    }
    numToGet = B3DMIN(numBytes - totalRecv, chunkSize);
    if (FinishGettingBuffer((char *)imArray + totalRecv, 0, numToGet, 
      numToGet)) {
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "PySEMSocket: Error %d while receiving image "
                "(chunk # %d) from server", WSAGetLastError(), chunk);
      mCloseBeforeNextUse = true;
      return 1;
    }
    totalRecv += numToGet;
  }
  return 0;
}

// Send the arguments from an image acquisition back then send the image if there is no
// error
int CPySEMSocket::SendImage(void *imArray, int imSize)
{
  int numChunks, chunkSize, numToSend, totalSent = 0;
  std::string bufCopy;
 
  // determine number of superchunks and send that back as long
  numChunks = (imSize + mSuperChunkSize - 1) / mSuperChunkSize;
  LONG_ARG(numChunks);
  SendAndReceiveArgs();
  if (mLongArgs[0]) {
    bufCopy = mErrorBuf;
    if (mLongArgs[0] != -9)
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Error %d returned in socket exchange with "
                "SerialEM to put image in buffer%s%s",  mLongArgs[0],
                 bufCopy.size() ? ": " : "", bufCopy.size() ? bufCopy.c_str() : "");

    if (mLongArgs[0] < 0)
      CloseServer();
    return 1;
  }

  // Loop on the chunks until done, getting acknowledgement after each
  chunkSize = (imSize + numChunks - 1) / numChunks;
  while (totalSent < imSize) {
    numToSend = chunkSize;
    if (chunkSize > imSize - totalSent)
      numToSend = imSize - totalSent;
    if (SendBuffer((char *)imArray + totalSent, numToSend))
      return 1;
    totalSent += numToSend;
  }
  return 0;
}

// Send a buffer, in chunks if necessary
int CPySEMSocket::SendBuffer(char *buffer, int numBytes)
{
  int numTotalSent = 0;
  int numToSend, numSent;
  while (numTotalSent < numBytes) {
    numToSend = numBytes - numTotalSent;
    if (numToSend > mChunkSize)
      numToSend = mChunkSize;
    numSent = (int)send(mServer, &buffer[numTotalSent], numToSend, 0);
    if (numSent < 0) {
      ReportErrorAndClose(numSent, "send a chunk of bytes");
      return 1;
    }
    numTotalSent += numSent;
  }
  return 0;
}

// Close the connection upon error; report it unless it is clearly a SerialEM disconnect
void CPySEMSocket::ReportErrorAndClose(int retval, const char *message)
{
  if (retval == SOCKET_ERROR) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "WSA Error %d on call to %s", 
              WSAGetLastError(), message);
  } else {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "retval %d on call to %s", 
      retval, message);
  }
  CloseServer();
}

// Unpack the received argument buffer, skipping over the first word with byte count
int CPySEMSocket::UnpackReceivedData(int limitedNum)
{
  int numBytes, numUnpacked = sizeof(int);

  if (mNumLongRecv > MAX_LONG_ARGS || mNumBoolRecv > MAX_BOOL_ARGS || 
    mNumDblRecv > MAX_DBL_ARGS)
    return 1;

  // If the message is basically empty then just let the caller report that; otherwise
  // then try to get the error code from the next word and return
  if (limitedNum > 0 && limitedNum < 8) {
    mLongArgs[0] = 0;
    return 0;
  }
  numBytes = mNumLongRecv * sizeof(LONG);
  if (limitedNum > 0)
    numBytes = 4;
  memcpy(mLongArgs, &mArgsBuffer[numUnpacked], numBytes);
  if (limitedNum > 0)
    return 0;
  numUnpacked += numBytes;
  numBytes = mNumBoolRecv * sizeof(BOOL);
  if (numBytes)
    memcpy(mBoolArgs, &mArgsBuffer[numUnpacked], numBytes);
  numUnpacked += numBytes;
  numBytes = mNumDblRecv * sizeof(double);
  if (numBytes)
    memcpy(mDoubleArgs, &mArgsBuffer[numUnpacked], numBytes);
  numUnpacked += numBytes;

  // If receiving a long array, size is in last long arg; copy address 
  if (mRecvLongArray && mNumLongRecv > 0) {
    mLongArray = (LONG *)(&mArgsBuffer[numUnpacked]);
    numUnpacked += sizeof(LONG) * mLongArgs[mNumLongRecv - 1];
  }
  return 0;
}

// Pack the data into the argument buffer as longs, BOOLS, doubles, and the long array
int CPySEMSocket::PackDataToSend()
{
  int numAdd;
  mNumBytesSend = sizeof(int);
  if (mNumLongSend) {
    numAdd = mNumLongSend * sizeof(LONG);
    if (numAdd + mNumBytesSend > mArgBufSize)
      return 1;
    memcpy(&mArgsBuffer[mNumBytesSend], mLongArgs, numAdd);
    mNumBytesSend += numAdd;
  }
  if (mNumBoolSend) {
    numAdd = mNumBoolSend * sizeof(BOOL);
    if (numAdd + mNumBytesSend > mArgBufSize)
      return 1;
    memcpy(&mArgsBuffer[mNumBytesSend], mBoolArgs, numAdd);
    mNumBytesSend += numAdd;
  }
  if (mNumDblSend) {
    numAdd = mNumDblSend * sizeof(double);
    if (numAdd + mNumBytesSend > mArgBufSize)
      return 1;
    memcpy(&mArgsBuffer[mNumBytesSend], mDoubleArgs, numAdd);
    mNumBytesSend += numAdd;
  }

  // If there is a long array to send, the last long arg has the size
  if (mLongArray) {
    numAdd = mLongArgs[mNumLongSend - 1] * sizeof(LONG);
    if (ReallocArgsBufIfNeeded(numAdd + mNumBytesSend))
      return 1;
    memcpy(&mArgsBuffer[mNumBytesSend], mLongArray, numAdd);
    mNumBytesSend += numAdd;
  }

  // Put the number of bytes at the beginning of the message
  memcpy(&mArgsBuffer[0], &mNumBytesSend, sizeof(int));
  return 0;
}

/*
 * COMMANDS FROM PYTHON
 */

// "Regular" command through CME codes, etc
int CPySEMSocket::RegularCommand(void)
{
  int ind, numLongs;
  double *dblArray;
  char *strArray;
  LONG *longArr = NULL;
  std::string bufCopy;
  InitializePacking(PSS_RegularCommand);
  LONG_ARG(mScriptData->functionCode);
  LONG_ARG(mScriptData->lastNonEmptyInd);
  if (mScriptData->lastNonEmptyInd > 0)
    longArr = AddItemArrays();
  else
    longArr = AddLongsAndStrings(NULL, 0, NULL, 0);
  
  if (!longArr) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE,
              "Error creating array for sending arguments to SerialEM");
    return 1;
  }
  mNumLongRecv = 3;
  mRecvLongArray = true;
  SendAndReceiveArgs();
  free(longArr);
  if (mLongArgs[0]) {
    bufCopy = mErrorBuf;
    if (mLongArgs[0] != -9)
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Error %d returned in socket exchange with "
                "SerialEM for regular command%s%s",  mLongArgs[0],
                bufCopy.size() ? ": " : "", bufCopy.size() ? bufCopy.c_str() : "");
    if (mLongArgs[0] < 0)
      CloseServer();
    return 1;
  }
  mScriptData->highestReportInd = mLongArgs[1];
  mScriptData->errorOccurred = mLongArgs[2];
  numLongs = mLongArgs[1] + 1;

  // Unpack the arrays and strings from the long arrays
  dblArray = (double *)(&mLongArray[numLongs]);
  strArray = (char *)(&dblArray[numLongs]);
  for (ind = 0; ind < numLongs; ind++) {
    mScriptData->repValIsString[ind] = mLongArray[ind] != 0;
    mScriptData->reportedVals[ind] = dblArray[ind];
    if (mLongArray[ind] != 0) {
      mScriptData->reportedStrs[ind] = strArray;
      strArray += strlen(strArray) + 1;
    } else {
      mScriptData->reportedStrs[ind] = "";
    }
  }
  return 0;
}

// OKtoRunExternalScript
int CPySEMSocket::OKtoRunExternalScript(BOOL &OKtoRun)
{
  std::string bufCopy;
  InitializePacking(PSS_OKtoRunExternalScript);
  mNumBoolRecv = 1;
  SendAndReceiveArgs();
  if (mLongArgs[0]) {
    bufCopy = mErrorBuf;
    if (mLongArgs[0] != -9)
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Error %d returned in socket exchange with "
                "SerialEM to check on running external script%s%s",  mLongArgs[0],
                bufCopy.size() ? ": " : "", bufCopy.size() ? bufCopy.c_str() : "");
    if (mLongArgs[0] < 0)
      CloseServer();
    return 1;
  }
  OKtoRun = mBoolArgs[0];
  return 0;
}

// GetBufferImage
void *CPySEMSocket::GetBufferImage(int bufInd, int ifFFT, const char *bufStr, int &imType,
                                   int &rowBytes, int &sizeX, int &sizeY, int &itemSize,
                                   char *format)
{
  char *imArray;
  int numBytes, numChunks;
  std::string bufCopy;
   InitializePacking(PSS_GetBufferImage);
  LONG_ARG(bufInd);
  LONG_ARG(ifFFT);
  mNumLongRecv = 6;
  SendAndReceiveArgs();
  if (mLongArgs[0]) {
     bufCopy = mErrorBuf;
    if (mLongArgs[0] != -9)
      sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Error %d returned in socket exchange with "
                "SerialEM to get buffer %s%s%s",  mLongArgs[0], bufStr,
                bufCopy.size() ? ": " : "", bufCopy.size() ? bufCopy.c_str() : "");
    if (mLongArgs[0] < 0)
      CloseServer();
    return NULL;
  }
  imType = mLongArgs[1];
  rowBytes = mLongArgs[2];
  sizeX = mLongArgs[3];
  sizeY = mLongArgs[4];
  numBytes = mLongArgs[5];
  numChunks = mLongArgs[6];
  if (!numBytes) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "There is no image in SerialEM buffer %s (%d %d)",
              bufStr, bufInd, ifFFT);
    return NULL;
  }

  switch (imType) {
  case MRC_MODE_BYTE:
    itemSize = 1;
    strcpy_s(format, 8, "B");
    break;
  case MRC_MODE_FLOAT:
    itemSize = 4;
    strcpy_s(format, 8, "f");
    break;
  case MRC_MODE_SHORT:
    itemSize = 2;
    strcpy_s(format, 8, "h");
    break;
  case MRC_MODE_USHORT:
    itemSize = 2;
    strcpy_s(format, 8, "H");
    break;
  case MRC_MODE_RGB:
    itemSize = 3;
    strcpy_s(format, 8, "BBB");
    break;
  default:
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "The image in buffer %s has mode %d which is"
              " unsupported", bufStr, imType);
    return NULL;
  }
  
  imArray = (char *)malloc(numBytes);
  if (!imArray) {
    sprintf_s(mErrorBuf, ERR_BUF_SIZE, "Failed to allocate array of %d bytes to hold "
              "image in buffer %s",  numBytes, bufStr);
    return NULL;
  }

  if (ReceiveImage(imArray, numBytes, numChunks)) {
    free(imArray);
    return NULL;
  }    
  return imArray;
}

// PutImageInbuffer
int CPySEMSocket::PutImageInbuffer(void *imArray, int imType, int sizeX, int sizeY,
                                   int itemSize, int toBuf, int baseBuf, int moreBinning,
                                   int capFlag)
{
  
  int arrSize = itemSize * sizeX * sizeY;
  InitializePacking(PSS_PutImageInbuffer);
  LONG_ARG(imType);
  LONG_ARG(sizeX);
  LONG_ARG(sizeY);
  LONG_ARG(arrSize);
  LONG_ARG(toBuf);
  LONG_ARG(baseBuf);
  LONG_ARG(moreBinning);
  LONG_ARG(capFlag);
  return SendImage(imArray, arrSize);
}
