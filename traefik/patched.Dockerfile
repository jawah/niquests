FROM winamd64/golang:1.25-nanoserver-ltsc2022 AS build

WORKDIR /go/src/github.com/mccutchen/go-httpbin

COPY . .

RUN mkdir dist
RUN go build -ldflags="-s" -o dist/go-httpbin.exe ./cmd/go-httpbin

FROM mcr.microsoft.com/windows/nanoserver:ltsc2022

COPY --from=build /go/src/github.com/mccutchen/go-httpbin/dist /app

WORKDIR /app

EXPOSE 8080
CMD ["/app/go-httpbin.exe"]
